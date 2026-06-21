use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};
use mavlink::ardupilotmega::{
    HEARTBEAT_DATA,
    ATTITUDE_DATA,
    GLOBAL_POSITION_INT_DATA,
    SYS_STATUS_DATA,
    VFR_HUD_DATA,
    SCALED_PRESSURE2_DATA,
    BATTERY_STATUS_DATA
};


#[derive(Serialize, Deserialize)]
pub struct Heartbeat {
    pub system_id: u8,
    pub component_id: u8,
    pub mav_type: u8,
    pub autopilot: u8,
    pub base_mode: u8,
    pub custom_mode: u32,
    pub system_status: u8,
    pub timestamp_us: u64,
}


#[derive(Serialize, Deserialize)]
pub struct SysStatus {
    pub sensors_present: u32,
    pub sensors_enabled: u32,
    pub sensors_health: u32,
    pub load: u16,
    pub voltage_battery: u16,
    pub current_battery: i16,
    pub battery_remaining: i8,
    pub drop_rate_comm: u16,
    pub errors_comm: u16,
    pub timestamp_us: u64,
}


#[derive(Serialize, Deserialize)]
pub struct Attitude {
    pub roll: f32,
    pub pitch: f32,
    pub yaw: f32,
    pub rollspeed: f32,
    pub pitchspeed: f32,
    pub yawspeed: f32,
    pub timestamp_us: u64,
}


#[derive(Serialize, Deserialize)]
pub struct GlobalPosition {
    pub lat: i32,
    pub lon: i32,
    pub alt: i32,
    pub relative_alt: i32,
    pub vx: i16,
    pub vy: i16,
    pub vz: i16,
    pub hdg: u16,
    pub timestamp_us: u64,
}


#[derive(Serialize, Deserialize)]
pub struct ScaledPressure2 {
    pub press_abs: f32,
    pub press_diff: f32,
    pub temperature: i16,
    pub timestamp_us: u64,
}


#[derive(Serialize, Deserialize)]
pub struct BatteryStatus {
    pub id: u8,
    pub battery_function: u8,
    pub battery_type: u8,
    pub temperature: i16,
    pub voltages: [u16; 10],
    pub current_battery: i16,
    pub current_consumed: i32,
    pub energy_consumed: i32,
    pub battery_remaining: i8,
    pub charge_state: u8,
    pub timestamp_us: u64,
}


#[derive(Serialize, Deserialize)]
pub struct VfrHud {
    pub airspeed: f32,
    pub groundspeed: f32,
    pub heading: i16,
    pub throttle: u16,
    pub alt: f32,
    pub climb: f32,
    pub timestamp_us: u64,
}


pub fn now_us() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Error")
        .as_micros() as u64
}


pub fn parse_heartbeat(header: &mavlink::MavHeader, hb: &HEARTBEAT_DATA, ts: u64) -> Heartbeat {
    Heartbeat {
        system_id: header.system_id,
        component_id: header.component_id,
        mav_type: hb.mavtype as u8,
        autopilot: hb.autopilot as u8,
        base_mode: hb.base_mode.bits(),
        custom_mode: hb.custom_mode,
        system_status: hb.system_status as u8,
        timestamp_us: ts,
    }
}


pub fn parse_attitude(att: &ATTITUDE_DATA, ts: u64) -> Attitude {
    Attitude {
        roll: att.roll,
        pitch: att.pitch,
        yaw: att.yaw,
        rollspeed: att.rollspeed,
        pitchspeed: att.pitchspeed,
        yawspeed: att.yawspeed,
        timestamp_us: ts,
    }
}


pub fn parse_global_position(pos: &GLOBAL_POSITION_INT_DATA, ts: u64) -> GlobalPosition {
    GlobalPosition {
        lat: pos.lat,
        lon: pos.lon,
        alt: pos.alt,
        relative_alt: pos.relative_alt,
        vx: pos.vx,
        vy: pos.vy,
        vz: pos.vz,
        hdg: pos.hdg,
        timestamp_us: ts,
    }
}


pub fn parse_sys_status(sys: &SYS_STATUS_DATA, ts: u64) -> SysStatus {
    SysStatus {
        sensors_present: sys.onboard_control_sensors_present.bits(),
        sensors_enabled: sys.onboard_control_sensors_enabled.bits(),
        sensors_health: sys.onboard_control_sensors_health.bits(),
        load: sys.load,
        voltage_battery: sys.voltage_battery,
        current_battery: sys.current_battery,
        battery_remaining: sys.battery_remaining,
        drop_rate_comm: sys.drop_rate_comm,
        errors_comm: sys.errors_comm,
        timestamp_us: ts,
    }
}


pub fn parse_vfr_hud(hud: &VFR_HUD_DATA, ts: u64) -> VfrHud {
    VfrHud {
        airspeed: hud.airspeed,
        groundspeed: hud.groundspeed,
        heading: hud.heading,
        throttle: hud.throttle,
        alt: hud.alt,
        climb: hud.climb,
        timestamp_us: ts,
    }
}


pub fn parse_scaled_pressure2(pres: &SCALED_PRESSURE2_DATA, ts: u64) -> ScaledPressure2 {
    ScaledPressure2 {
        press_abs: pres.press_abs,
        press_diff: pres.press_diff,
        temperature: pres.temperature,
        timestamp_us: ts,
    }
}


pub fn parse_battery_status(bat: &BATTERY_STATUS_DATA, ts: u64) -> BatteryStatus {
    BatteryStatus {
        id: bat.id,
        battery_function: bat.battery_function as u8,
        battery_type: bat.mavtype as u8,
        temperature: bat.temperature,
        voltages: bat.voltages,
        current_battery: bat.current_battery,
        current_consumed: bat.current_consumed,
        energy_consumed: bat.energy_consumed,
        battery_remaining: bat.battery_remaining,
        charge_state: 0,
        timestamp_us: ts,
    }
}
