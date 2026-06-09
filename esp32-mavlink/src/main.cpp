#include <Arduino.h>
#include <common/mavlink.h>

#define BAUD_RATE 57600
#define SYS_ID 1
#define COMP_ID MAV_COMP_ID_AUTOPILOT1

static uint8_t status_idx = 0;
static uint32_t statustext_timer = 0;
static uint32_t boot_ms;
static float elapsed_s() { return (millis() - boot_ms) / 1000.0f; }
static uint32_t elapsed_ms() { return millis() - boot_ms; }
static float sim_roll() { return 0.3f  * sinf(elapsed_s()); }
static float sim_pitch() { return 0.15f * sinf(elapsed_s() * 0.7f); }
static float sim_yaw() { return fmodf(elapsed_s() * 0.1f, 2.0f * PI); }
static float sim_depth() { return 5.0f + 4.0f * sinf(elapsed_s() * 0.2f); }
static float sim_speed() { return 0.5f + 0.3f * sinf(elapsed_s() * 0.4f); }
static uint8_t sim_batt() { return (uint8_t)max(0.0f, 95.0f - elapsed_s() * 0.005f); }

static const char* status_msgs[] = {
    "BlueROV2 ready",
    "Depth hold active",
    "All systems nominal",
    "Battery OK",
};


static void mav_send(mavlink_message_t& msg) {
    uint8_t buf[MAVLINK_MAX_PACKET_LEN];
    uint16_t len = mavlink_msg_to_send_buffer(buf, &msg);
    Serial.write(buf, len);
}


void send_heartbeat() {
    mavlink_message_t msg;
    mavlink_msg_heartbeat_pack(
        SYS_ID,
        COMP_ID,
        &msg,
        MAV_TYPE_SUBMARINE,
        MAV_AUTOPILOT_ARDUPILOTMEGA,
        MAV_MODE_FLAG_STABILIZE_ENABLED | MAV_MODE_FLAG_SAFETY_ARMED,
        0,
        MAV_STATE_ACTIVE
    );
    mav_send(msg);
}


void send_sys_status() {
    uint32_t sensors =
        MAV_SYS_STATUS_SENSOR_3D_GYRO |
        MAV_SYS_STATUS_SENSOR_3D_ACCEL |
        MAV_SYS_STATUS_SENSOR_3D_MAG |
        MAV_SYS_STATUS_SENSOR_ABSOLUTE_PRESSURE |
        MAV_SYS_STATUS_SENSOR_GPS;
    mavlink_message_t msg;
    mavlink_msg_sys_status_pack(
        SYS_ID,
        COMP_ID,
        &msg,
        sensors,
        sensors,
        sensors,
        300,
        14800,
        2500,
        sim_batt(),
        0, 0, 0, 0, 0, 0,
        0, 0, 0
    );
    mav_send(msg);
}


void send_attitude() {
    float ts = elapsed_s();
    mavlink_message_t msg;
    mavlink_msg_attitude_pack(
        SYS_ID,
        COMP_ID,
        &msg,
        elapsed_ms(),
        sim_roll(), sim_pitch(), sim_yaw(),
        0.02f * cosf(ts),
        0.01f * cosf(ts * 0.7f),
        0.01f
    );
    mav_send(msg);
}


void send_global_position() {
    float ts = elapsed_s();
    int32_t lat = (int32_t)((-27.5969f + 0.0001f * sinf(ts * 0.3f)) * 1e7f);
    int32_t lon = (int32_t)((-48.5495f + 0.0001f * cosf(ts * 0.3f)) * 1e7f);
    int32_t alt = (int32_t)(-sim_depth() * 1000.0f);
    uint16_t hdg = (uint16_t)(fmodf(ts * 5.0f, 360.0f) * 100.0f);
    mavlink_message_t msg;
    mavlink_msg_global_position_int_pack(
        SYS_ID,
        COMP_ID,
        &msg,
        elapsed_ms(),
        lat,
        lon,
        alt,
        0, 0, 0, 0,
        hdg
    );
    mav_send(msg);
}


void send_scaled_pressure2() {
    float press_abs = 1013.25f + sim_depth() * 9.8f;
    mavlink_message_t msg;
    mavlink_msg_scaled_pressure2_pack(
        SYS_ID,
        COMP_ID,
        &msg,
        elapsed_ms(),
        press_abs,
        0.0f,
        2000,
        0
    );
    mav_send(msg);
}


void send_battery_status() {
    uint16_t cells[10] = {
        3750, 3700, 3680, 3670,
        UINT16_MAX, UINT16_MAX, UINT16_MAX,
        UINT16_MAX, UINT16_MAX, UINT16_MAX
    };
    uint16_t cells_ext[4] = {0, 0, 0, 0};
    mavlink_message_t msg;
    mavlink_msg_battery_status_pack(
        SYS_ID,
        COMP_ID,
        &msg,
        0,
        MAV_BATTERY_FUNCTION_ALL,
        MAV_BATTERY_TYPE_LIPO,
        2000,
        cells,
        2500,
        -1,
        -1,
        sim_batt(),
        -1,
        MAV_BATTERY_CHARGE_STATE_OK,
        cells_ext,
        0, 0
    );
    mav_send(msg);
}


void send_vfr_hud() {
    float ts = elapsed_s();
    mavlink_message_t msg;
    mavlink_msg_vfr_hud_pack(
        SYS_ID,
        COMP_ID,
        &msg,
        sim_speed(),
        sim_speed() * 0.9f,
        (int16_t)fmodf(ts * 5.0f, 360.0f),
        (uint16_t)(30 + 20 * sinf(ts * 0.3f)),
        -sim_depth(),
        0.05f * cosf(ts * 0.4f)
    );
    mav_send(msg);
}


void send_statustext(const char* text, uint8_t severity) {
    mavlink_message_t msg;
    mavlink_msg_statustext_pack(
        SYS_ID,
        COMP_ID,
        &msg,
        severity,
        text,
        0,
        0
    );
    mav_send(msg);
}


struct Task { 
    uint32_t interval_ms;
    uint32_t last_run;
    void (*fn)();
};

static Task tasks[] = {
    {1000, 0, send_heartbeat},
    {1000, 0, send_sys_status},
    {100, 0, send_attitude},
    {200, 0, send_global_position},
    {100, 0, send_scaled_pressure2},
    {1000, 0, send_battery_status},
    {200, 0, send_vfr_hud},
};


void setup() {
    Serial.begin(BAUD_RATE);
    boot_ms = millis();
    delay(500);
    send_statustext("BlueROV2 booting", MAV_SEVERITY_INFO);
}


void loop() {
    uint32_t now = millis();
    for (auto& t : tasks) {
        if (now - t.last_run >= t.interval_ms) {
            t.last_run = now;
            t.fn();
        }
    }
    if (now - statustext_timer >= 15000) {
        statustext_timer = now;
        send_statustext(status_msgs[status_idx % 4], MAV_SEVERITY_INFO);
        status_idx++;
    }
}
