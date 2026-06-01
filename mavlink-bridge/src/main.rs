use mavlink::MavConnection;
use serde::{Deserialize, Serialize};
use mavlink::ardupilotmega::MavMessage;
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


#[tokio::main]
async fn main() -> anyhow::Result<()>{

    let connect = std::env::var("ZENOH_CONNECT").unwrap_or_else(|_| "tcp/localhost:7447".to_string());
    let config = zenoh::Config::from_json5(&format!(
        r#"{{"mode":"client","connect":{{"endpoints":["{connect}"]}}}}"#
    )).map_err(|e| anyhow::anyhow!("{e}"))?;
    let session = zenoh::open(config).await.map_err(|e| anyhow::anyhow!("{e}"))?;

    let pub_heartbeat = session.declare_publisher("rov/heartbeat").await.map_err(|e| anyhow::anyhow!("{e}"))?;
    let pub_attitude = session.declare_publisher("rov/attitude").await.map_err(|e| anyhow::anyhow!("{e}"))?;
    let pub_position = session.declare_publisher("rov/position").await.map_err(|e| anyhow::anyhow!("{e}"))?;

    let (tx, mut rx) = tokio::sync::mpsc::channel::<(mavlink::MavHeader, MavMessage)>(100);

    std::thread::spawn(move || {
        let mavlink_udp = std::env::var("MAVLINK_LISTEN").unwrap_or_else(|_| "udpin:0.0.0.0:14550".to_string());
        let mut vehicle = mavlink::connect::<MavMessage>(&mavlink_udp).unwrap();
        vehicle.set_allow_recv_any_version(true);

        eprintln!("[bridge] MAVLink listening on {}", mavlink_udp);
        
        loop {
            match vehicle.recv() {
                Ok((header, msg)) => {
                    eprintln!("[bridge] received sys={} type={:?}", header.system_id, msg);
                    let _ = tx.blocking_send((header, msg));
                }
                Err(e) => {
                    eprintln!("[bridge] recv error: {:?}", e);
                }
            }
        }
    });

    let mut sigterm = signal(SignalKind::terminate())?;
    loop {
        tokio::select! {
            _ = tokio::signal::ctrl_c() => break,
            _ = sigterm.recv() => break,
            msg = rx.recv() => {
                if let Some((header, msg)) = msg {
                    match msg {
                        MavMessage::HEARTBEAT(hb) => {
                            let hb_data =  Heartbeat {
                                system_id: header.system_id,
                                status: format!("{:?}", hb.system_status),
                                timestamp_us: now_us(),
                            };
                            pub_heartbeat.put(serde_json::to_string(&hb_data)?)
                            .await.map_err(|e| anyhow::anyhow!("{e}"))?;
                        },
                        MavMessage::ATTITUDE(att) => {
                            let att_data = Attitude {
                                roll: att.roll as f64,
                                pitch: att.pitch as f64,
                                yaw: att.yaw as f64,
                                timestamp_us: now_us(),
                            };
                            pub_attitude.put(serde_json::to_string(&att_data)?)
                            .await.map_err(|e| anyhow::anyhow!("{e}"))?;
                        },
                        MavMessage::GLOBAL_POSITION_INT(pos) => {
                            let pos_data = GlobalPosition {
                                lat: pos.lat as f64 / 1e7,
                                lon: pos.lon as f64 / 1e7,
                                alt_m: pos.alt as f64 / 1000.0,
                                heading_deg: if pos.hdg == 65535 { 0.0 } else { pos.hdg as f64 / 100.0 },
                                timestamp_us: now_us(),
                            };
                            pub_position.put(serde_json::to_string(&pos_data)?)
                            .await.map_err(|e| anyhow::anyhow!("{e}"))?;
                        },
                        _ => {}
                    }
                }
            }
        }
    }
    Ok(())
}
