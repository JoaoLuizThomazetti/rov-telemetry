use std::fs::File;
use std::io::BufWriter;
use std::collections::BTreeMap;
use std::time::{SystemTime, UNIX_EPOCH};

use tokio::time::Duration;
use zenoh::config::Config;
use mcap::records::MessageHeader;
use serde::{Deserialize, Serialize};


#[derive(Serialize, Deserialize)]
struct Heartbeat {
    system_id: u8,
    status: String,
    timestamp_us: u64,
}

#[derive(Serialize, Deserialize)]
struct Attitude {
    roll: f64,
    pitch: f64,
    yaw: f64,
    timestamp_us: u64,
}

#[derive(Serialize, Deserialize)]
struct GlobalPosition {
    lat: f64,
    lon: f64,
    alt_m: f64,
    heading_deg: f64,
    timestamp_us: u64,
}


fn now_us() -> u64 {
    SystemTime::now()
    .duration_since(UNIX_EPOCH)
    .expect("Error")
    .as_micros() as u64
}


fn heartbeat() -> Heartbeat {
    Heartbeat {
        system_id: 1,
        status: "active".to_string(),
        timestamp_us: now_us(),
    }
}


fn simulate_attitude(t: f64) -> Attitude {
    Attitude {
        roll: 0.3 * t.sin(),
        pitch: 0.15 * (t * 0.7).sin(),
        yaw: 0.1 * t,
        timestamp_us: now_us(),
    }
}


fn simulate_position(t: f64) -> GlobalPosition {
    GlobalPosition {
        lat: -27.5969 + 0.0001 * (t * 0.3).sin(),
        lon: -48.5495 + 0.0001 * (t * 0.3).cos(),
        alt_m: 10.0 + 2.0 * (t * 0.5).sin(),
        heading_deg: (t * 5.0) % 360.0,
        timestamp_us: now_us(),
    }
}


fn setup_mcap() -> anyhow::Result<(mcap::Writer<BufWriter<File>>, u16, u16, u16)> {
    let mcap_dir = std::env::var("MCAP_DIR").unwrap_or_else(|_| ".".to_string());
    let path = format!("{}/recording.mcap", mcap_dir);
    let file = File::create(&path)?;

    let mut writer = mcap::Writer::new(BufWriter::new(file))?;

    let sch_hb  = writer.add_schema("heartbeat", "jsonschema", b"{}")?;
    let sch_att = writer.add_schema("attitude",  "jsonschema", b"{}")?;
    let sch_pos = writer.add_schema("position",  "jsonschema", b"{}")?;

    let metadata = BTreeMap::new();

    let ch_hb  = writer.add_channel(sch_hb,  "rov/heartbeat", "json", &metadata)?;
    let ch_att = writer.add_channel(sch_att, "rov/attitude",  "json", &metadata)?;
    let ch_pos = writer.add_channel(sch_pos, "rov/position",  "json", &metadata)?;

    Ok(( writer, ch_hb, ch_att, ch_pos ))
}


fn write_mcap<T: serde::Serialize>(
    writer: &mut mcap::Writer<BufWriter<File>>,
    ch: u16,
    seq: u32,
    data: &T
) -> anyhow::Result<()> {
    writer.write_to_known_channel(
        &MessageHeader {
            channel_id: ch,
            sequence: seq,
            log_time: now_us() * 1000,
            publish_time: now_us() * 1000,
        },
        &serde_json::to_vec(data)?,
    )?;
    Ok(())
}


#[tokio::main]
async fn main() -> anyhow::Result<()>{

    let session = zenoh::open(Config::default()).await.map_err(|e| anyhow::anyhow!("{e}"))?;
    
    let connect = std::env::var("ZENOH_CONNECT")
        .unwrap_or_else(|_| "tcp/localhost:7447".to_string());
    let config = zenoh::Config::from_json5(&format!(
        r#"{{"mode":"client","connect":{{"endpoints":["{connect}"]}}}}"#
    )).map_err(|e| anyhow::anyhow!("{e}"))?;
    let session = zenoh::open(config).await.map_err(|e| anyhow::anyhow!("{e}"))?;

    let pub_heartbeat = session.declare_publisher("rov/heartbeat")
        .await.map_err(|e| anyhow::anyhow!("{e}"))?;
    let pub_attitude = session.declare_publisher("rov/attitude")
        .await.map_err(|e| anyhow::anyhow!("{e}"))?;
    let pub_position = session.declare_publisher("rov/position")
        .await.map_err(|e| anyhow::anyhow!("{e}"))?;

    let start = tokio::time::Instant::now();

    let ( mut writer, ch_hb, ch_att, ch_pos ) = setup_mcap()?;
    let mut sequence: u32 = 0;

    loop {
        tokio::select! {
          _ = tokio::signal::ctrl_c() => break,
          _ = tokio::time::sleep(Duration::from_millis(100)) => {
            let t = start.elapsed().as_secs_f64();

            let hb_data: Heartbeat = heartbeat();
            pub_heartbeat.put(serde_json::to_string(&hb_data)?)
                .await.map_err(|e| anyhow::anyhow!("{e}"))?;
            write_mcap(&mut writer, ch_hb, sequence, &hb_data)?;

            let att_data: Attitude = simulate_attitude(t);
            pub_attitude.put(serde_json::to_string(&att_data)?)
                .await.map_err(|e| anyhow::anyhow!("{e}"))?;
            write_mcap(&mut writer, ch_att, sequence, &att_data)?;

            let pos_data: GlobalPosition = simulate_position(t);
            pub_position.put(serde_json::to_string(&pos_data)?)
                .await.map_err(|e| anyhow::anyhow!("{e}"))?;
            write_mcap(&mut writer, ch_pos, sequence, &pos_data)?;

            sequence = sequence.wrapping_add(1)
          }
        }
    }
    writer.finish()?;
    Ok(())
}
