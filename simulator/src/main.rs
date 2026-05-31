use tokio::time::Duration;
use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};
use tokio::signal::unix::{signal, SignalKind};


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


#[tokio::main]
async fn main() -> anyhow::Result<()>{
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
    let mut sigterm = signal(SignalKind::terminate())?;
    loop {
        tokio::select! {
          _ = tokio::signal::ctrl_c() => break,
          _ = sigterm.recv() => break,
          _ = tokio::time::sleep(Duration::from_millis(100)) => {
            let t = start.elapsed().as_secs_f64();
            let hb_data: Heartbeat = heartbeat();
            pub_heartbeat.put(serde_json::to_string(&hb_data)?)
                .await.map_err(|e| anyhow::anyhow!("{e}"))?;
            let att_data: Attitude = simulate_attitude(t);
            pub_attitude.put(serde_json::to_string(&att_data)?)
                .await.map_err(|e| anyhow::anyhow!("{e}"))?;
            let pos_data: GlobalPosition = simulate_position(t);
            pub_position.put(serde_json::to_string(&pos_data)?)
                .await.map_err(|e| anyhow::anyhow!("{e}"))?;
          }
        }
    }
    Ok(())
}
