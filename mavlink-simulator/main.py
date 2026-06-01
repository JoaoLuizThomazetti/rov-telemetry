import os
import time
import math
import signal
import threading
from pymavlink import mavutil


TARGET = os.getenv('MAVLINK_TARGET', 'udpout:127.0.0.1:14550')
conn = mavutil.mavlink_connection(TARGET, source_system=1)


def simulate_attitude(t: float) -> tuple[float, float, float]:
    roll =  0.3 * math.sin(t)
    pitch = 0.15 * math.sin(t * 0.7)
    yaw = 0.1 * t
    return roll, pitch, yaw


def simulate_position(t: float) -> tuple[float, float, float]:
    roll =  0.3 * math.sin(t)
    pitch = 0.15 * math.sin(t * 0.7)
    yaw = 0.1 * t
    return roll, pitch, yaw


def send_heartbeat():
    while True:
        conn.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_SUBMARINE,
            mavutil.mavlink.MAV_AUTOPILOT_GENERIC,
            0, 0,
            mavutil.mavlink.MAV_STATE_ACTIVE,
            3
        )
        time.sleep(1)


def send_attitude(boot_time: int):
    while True:
        elapsed_time = (int(time.time() * 1000) - boot_time) & 0xFFFFFFFF
        roll, pitch, yaw = simulate_attitude(elapsed_time / 1000)
        conn.mav.attitude_send(
            elapsed_time,
            roll,
            pitch,
            yaw,
            0.0,
            0.0,
            0.0
        )
        time.sleep(0.1)


def send_global_position(boot_time: int):
    while True:
        elapsed_time = (int(time.time() * 1000) - boot_time) & 0xFFFFFFFF
        t = elapsed_time / 1000.0
        conn.mav.global_position_int_send(
            elapsed_time,
            int((-27.5969 + 0.0001 * math.sin(t * 0.3)) * 1e7),
            int((-48.5495 + 0.0001 * math.cos(t * 0.3)) * 1e7),
            int((10.0 + 2.0 * math.sin(t * 0.5)) * 1000),
            0,
            0, 0, 0,
            int((t * 5.0) % 360.0 * 100)
        )
        time.sleep(0.1)


def main():
    boot_time = int(time.time() * 1000)
    threads = [
        threading.Thread(target=send_heartbeat, daemon=True),
        threading.Thread(target=send_attitude, args=(boot_time,), daemon=True),
        threading.Thread(target=send_global_position, args=(boot_time,), daemon=True),
    ]
    print("- Initiating threads")
    for t in threads:
        t.start()
    signal.pause()


if __name__ == "__main__":
    main()
