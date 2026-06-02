import os
import time
import math
import threading
from typing import Callable
from pymavlink import mavutil


TARGET = os.getenv('MAVLINK_TARGET', 'udpout:127.0.0.1:14550')
CONN = None


def get_conn():
    global CONN
    if CONN is None:
        CONN = mavutil.mavlink_connection(TARGET, source_system=1)
    return CONN


def simulate_attitude(t: float) -> tuple[float, float, float]:
    roll = 0.3 * math.sin(t)
    pitch = 0.15 * math.sin(t * 0.7)
    yaw = (0.1 * t) % (2 * math.pi)
    return roll, pitch, yaw


def simulate_position(t: float) -> tuple[float, float, float, int]:
    lat = int((-27.5969 + 0.0001 * math.sin(t * 0.3)) * 1e7)
    lon = int((-48.5495 + 0.0001 * math.cos(t * 0.3)) * 1e7)
    alt = int((10.0 + 2.0 * math.sin(t * 0.5)) * 1000)
    head = int(((t * 5.0) % 360.0 ) * 100)
    return lat, lon, alt, head


def send_heartbeat(_: int) -> None:
    get_conn().mav.heartbeat_send(
        mavutil.mavlink.MAV_TYPE_SUBMARINE,
        mavutil.mavlink.MAV_AUTOPILOT_GENERIC,
        0, 0,
        mavutil.mavlink.MAV_STATE_ACTIVE,
        3
    )


def send_attitude(boot_time: int) -> None:
    elapsed_time = (int(time.time() * 1000) - boot_time) & 0xFFFFFFFF
    roll, pitch, yaw = simulate_attitude(elapsed_time / 1000.0)
    get_conn().mav.attitude_send(
        elapsed_time,
        roll,
        pitch,
        yaw,
        0.0,
        0.0,
        0.0
    )


def send_global_position(boot_time: int) -> None:
    elapsed_time = (int(time.time() * 1000) - boot_time) & 0xFFFFFFFF
    lat, lon, alt, head = simulate_position(elapsed_time / 1000.0)
    get_conn().mav.global_position_int_send(
        elapsed_time,
        lat,
        lon,
        alt,
        0,
        0, 0, 0,
        head
    )


def handle_loop(boot_time: int, frequency: float, function: Callable) -> None:
    while True:
        function(boot_time)
        time.sleep(frequency)


def main() -> None:
    boot_time = int(time.time() * 1000)
    threads = [
        threading.Thread(target=handle_loop, args=(boot_time, 1.0, send_heartbeat), daemon=True),
        threading.Thread(target=handle_loop, args=(boot_time, 0.1, send_attitude), daemon=True),
        threading.Thread(target=handle_loop, args=(boot_time, 0.1, send_global_position), daemon=True),
    ]
    print("- Initiating threads")
    for t in threads:
        t.start()
    threading.Event().wait()


if __name__ == "__main__":
    main()
