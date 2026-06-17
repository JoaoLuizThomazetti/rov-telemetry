mod handle_messages;

use crate::handle_messages::*;
use mavlink::{MavConnection, MavHeader};
use tokio::signal::unix::{signal, SignalKind};
use mavlink::ardupilotmega::MavMessage;
use std::sync::Arc;
use dashmap::DashMap;


#[tokio::main]
async fn main() -> anyhow::Result<()>{
    env_logger::init();
    
    let payload_cache: Arc<DashMap<String, String>> = Arc::new(DashMap::new());

    let connect = std::env::var("ZENOH_CONNECT").unwrap_or_else(|_| "tcp/localhost:7447".to_string());
    let config = zenoh::Config::from_json5(&format!(
        r#"{{"mode":"client","connect":{{"endpoints":["{connect}"]}}}}"#
    )).map_err(|e| anyhow::anyhow!("{e}"))?;
    let session = zenoh::open(config).await.map_err(|e| anyhow::anyhow!("{e}"))?;

    let pub_heartbeat = session.declare_publisher("rov/heartbeat").await.map_err(|e| anyhow::anyhow!("{e}"))?;
    let pub_sys_status = session.declare_publisher("rov/sys_status").await.map_err(|e| anyhow::anyhow!("{e}"))?;
    let pub_attitude = session.declare_publisher("rov/attitude").await.map_err(|e| anyhow::anyhow!("{e}"))?;
    let pub_global_position = session.declare_publisher("rov/global_position").await.map_err(|e| anyhow::anyhow!("{e}"))?;
    let pub_vfr_hud = session.declare_publisher("rov/vfr_hud").await.map_err(|e| anyhow::anyhow!("{e}"))?;
    let pub_scaled_pressure2 = session.declare_publisher("rov/scaled_pressure2").await.map_err(|e| anyhow::anyhow!("{e}"))?;
    let pub_battery_status = session.declare_publisher("rov/battery_status").await.map_err(|e| anyhow::anyhow!("{e}"))?;
    let queryable = session.declare_queryable("rov/**").await.map_err(|e| anyhow::anyhow!("{e}"))?;

    let (tx, mut rx) = tokio::sync::mpsc::channel::<(MavHeader, MavMessage)>(100);

    std::thread::spawn(move || {
        let mavlink_udp = std::env::var("MAVLINK_LISTEN").unwrap_or_else(|_| "udpin:0.0.0.0:14550".to_string());
        let mut vehicle = mavlink::connect::<MavMessage>(&mavlink_udp).unwrap();
        vehicle.set_allow_recv_any_version(true);

        log::info!("[bridge] MAVLink listening on {}", mavlink_udp);
        
        loop {
            match vehicle.recv() {
                Ok((header, msg)) => {
                    log::debug!("[bridge] received sys={} type={:?}", header.system_id, msg);
                    let _ = tx.blocking_send((header, msg));
                }
                Err(e) => {
                    log::warn!("[bridge] recv error: {:?}", e);
                }
            }
        }
    });

    let mut sigterm = signal(SignalKind::terminate())?;
    loop {
        tokio::select! {
            _ = tokio::signal::ctrl_c() => break,
            _ = sigterm.recv() => break,
            Ok(query) = queryable.recv_async() => {
                let key = query.key_expr().to_string();
                if let Some(payload) = payload_cache.get(&key) {
                    let _ = query.reply(key, payload.clone()).await;
                }
            },
            msg = rx.recv() => {
                if let Some((header, msg)) = msg {
                    match msg {
                        MavMessage::HEARTBEAT(hb) => {
                            let hb_data = parse_heartbeat(&header, &hb, now_us());
                            let str_hb_data = serde_json::to_string(&hb_data).map_err(|e| anyhow::anyhow!("{e}"))?;
                            pub_heartbeat.put(&str_hb_data).await.map_err(|e| anyhow::anyhow!("{e}"))?;
                            payload_cache.insert(pub_heartbeat.key_expr().to_string(), str_hb_data.clone());
                        },
                        MavMessage::SYS_STATUS(sys) => {
                            let sys_data = parse_sys_status(&sys, now_us());
                            let str_sys_data = serde_json::to_string(&sys_data).map_err(|e| anyhow::anyhow!("{e}"))?;
                            pub_sys_status.put(&str_sys_data).await.map_err(|e| anyhow::anyhow!("{e}"))?;
                            payload_cache.insert(pub_sys_status.key_expr().to_string(), str_sys_data.clone());
                        },
                        MavMessage::ATTITUDE(att) => {
                            let att_data = parse_attitude(&att, now_us());
                            let str_att_data = serde_json::to_string(&att_data).map_err(|e| anyhow::anyhow!("{e}"))?;
                            pub_attitude.put(&str_att_data).await.map_err(|e| anyhow::anyhow!("{e}"))?;
                            payload_cache.insert(pub_attitude.key_expr().to_string(), str_att_data.clone());
                        },
                        MavMessage::GLOBAL_POSITION_INT(pos) => {
                            let pos_data = parse_global_position(&pos, now_us());
                            let str_pos_data = serde_json::to_string(&pos_data).map_err(|e| anyhow::anyhow!("{e}"))?;
                            pub_global_position.put(&str_pos_data).await.map_err(|e| anyhow::anyhow!("{e}"))?;
                            payload_cache.insert(pub_global_position.key_expr().to_string(), str_pos_data.clone());
                        },
                        MavMessage::VFR_HUD(hud) => {
                            let hud_data = parse_vfr_hud(&hud, now_us());
                            let str_hud_data = serde_json::to_string(&hud_data).map_err(|e| anyhow::anyhow!("{e}"))?;
                            pub_vfr_hud.put(&str_hud_data).await.map_err(|e| anyhow::anyhow!("{e}"))?;
                            payload_cache.insert(pub_vfr_hud.key_expr().to_string(), str_hud_data.clone());
                        },
                        MavMessage::SCALED_PRESSURE2(pres) => {
                            let pres_data = parse_scaled_pressure2(&pres, now_us());
                            let str_pres_data = serde_json::to_string(&pres_data).map_err(|e| anyhow::anyhow!("{e}"))?;
                            pub_scaled_pressure2.put(&str_pres_data).await.map_err(|e| anyhow::anyhow!("{e}"))?;
                            payload_cache.insert(pub_scaled_pressure2.key_expr().to_string(), str_pres_data.clone());
                        },
                        MavMessage::BATTERY_STATUS(bat) => {
                            let bat_data = parse_battery_status(&bat, now_us());
                            let str_bat_data = serde_json::to_string(&bat_data).map_err(|e| anyhow::anyhow!("{e}"))?;
                            pub_battery_status.put(&str_bat_data).await.map_err(|e| anyhow::anyhow!("{e}"))?;
                            payload_cache.insert(pub_battery_status.key_expr().to_string(), str_bat_data.clone());
                        },
                        _ => {}
                    }
                }
            }
        }
    }
    Ok(())
}


#[cfg(test)]
mod tests {
    use super::*;
    use mavlink::ardupilotmega::{
        MavState, MavType, MavAutopilot, MavModeFlag,
        HEARTBEAT_DATA, ATTITUDE_DATA, GLOBAL_POSITION_INT_DATA,
        VFR_HUD_DATA, SCALED_PRESSURE2_DATA,
    };

    #[test]
    fn test_parse_heartbeat() {
        let header = MavHeader { system_id: 1, component_id: 1, sequence: 0 };
        let hb = HEARTBEAT_DATA {
            custom_mode: 0,
            mavtype: MavType::MAV_TYPE_SUBMARINE,
            autopilot: MavAutopilot::MAV_AUTOPILOT_GENERIC,
            base_mode: MavModeFlag::empty(),
            system_status: MavState::MAV_STATE_ACTIVE,
            mavlink_version: 3,
        };
        let ts = now_us();
        let result = parse_heartbeat(&header, &hb, ts);
        assert_eq!(result.system_id, 1);
        assert_eq!(result.component_id, 1);
        assert_eq!(result.system_status, MavState::MAV_STATE_ACTIVE as u8);
        assert_eq!(result.timestamp_ms, ts);
    }

    #[test]
    fn test_parse_attitude() {
        let att = ATTITUDE_DATA {
            time_boot_ms: 0,
            roll: 0.5_f32,
            pitch: 0.3_f32,
            yaw: 1.2_f32,
            rollspeed: 0.1_f32,
            pitchspeed: 0.2_f32,
            yawspeed: 0.3_f32,
        };
        let ts = now_us();
        let result = parse_attitude(&att, ts);
        assert_eq!(result.roll, 0.5_f32);
        assert_eq!(result.pitch, 0.3_f32);
        assert_eq!(result.yaw, 1.2_f32);
        assert_eq!(result.rollspeed, 0.1_f32);
        assert_eq!(result.pitchspeed, 0.2_f32);
        assert_eq!(result.yawspeed, 0.3_f32);
        assert_eq!(result.timestamp_ms, ts);
    }

    #[test]
    fn test_parse_global_position() {
        let pos = GLOBAL_POSITION_INT_DATA {
            time_boot_ms: 0,
            lat: -275969000_i32,
            lon: -485495000_i32,
            alt: 10000_i32,
            relative_alt: 0,
            vx: 0, vy: 0, vz: 0,
            hdg: 18000_u16,
        };
        let ts = now_us();
        let result = parse_global_position(&pos, ts);
        assert_eq!(result.lat, -275969000_i32);
        assert_eq!(result.lon, -485495000_i32);
        assert_eq!(result.alt, 10000_i32);
        assert_eq!(result.hdg, 18000_u16);
        assert_eq!(result.timestamp_ms, ts);
    }

    #[test]
    fn test_parse_global_position_unknown_heading() {
        let pos = GLOBAL_POSITION_INT_DATA {
            time_boot_ms: 0,
            lat: -275969000_i32,
            lon: -485495000_i32,
            alt: 10000_i32,
            relative_alt: 0,
            vx: 0, vy: 0, vz: 0,
            hdg: 65535_u16,
        };
        let ts = now_us();
        let result = parse_global_position(&pos, ts);
        assert_eq!(result.hdg, 65535_u16);
        assert_eq!(result.timestamp_ms, ts);
    }

    #[test]
    fn test_parse_vfr_hud() {
        let hud = VFR_HUD_DATA {
            airspeed: 1.5_f32,
            groundspeed: 1.2_f32,
            alt: -2.5_f32,
            climb: 0.1_f32,
            heading: 271_i16,
            throttle: 40_u16,
        };
        let ts = now_us();
        let result = parse_vfr_hud(&hud, ts);
        assert_eq!(result.airspeed, 1.5_f32);
        assert_eq!(result.groundspeed, 1.2_f32);
        assert_eq!(result.heading, 271_i16);
        assert_eq!(result.throttle, 40_u16);
        assert_eq!(result.alt, -2.5_f32);
        assert_eq!(result.timestamp_ms, ts);
    }

    #[test]
    fn test_parse_scaled_pressure2() {
        let pres = SCALED_PRESSURE2_DATA {
            time_boot_ms: 0,
            press_abs: 1042.85_f32,
            press_diff: 0.0_f32,
            temperature: 2000_i16,
        };
        let ts = now_us();
        let result = parse_scaled_pressure2(&pres, ts);
        assert_eq!(result.press_abs, 1042.85_f32);
        assert_eq!(result.press_diff, 0.0_f32);
        assert_eq!(result.temperature, 2000_i16);
        assert_eq!(result.timestamp_ms, ts);
    }
}
