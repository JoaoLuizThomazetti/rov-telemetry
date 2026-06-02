import math
import pytest
from pymavlink import mavutil
from unittest.mock import patch, MagicMock
from main import (
    simulate_attitude,
    simulate_position,
    send_heartbeat,
    send_attitude,
    send_global_position,
)


# ======== simulation
def test_simulate_attitude(): 
    roll, pitch, yaw = simulate_attitude(0.0)
    assert roll == 0.0
    assert pitch == 0.0
    assert yaw == 0.0
    roll, pitch, yaw = simulate_attitude(10.0)
    assert roll == -0.16320633326681092
    assert pitch == 0.09854798980781836
    assert yaw ==  1.0


def test_simulate_attitude_ranges():
    for t in [t * 0.1 for t in range(0, 1000)]:
        roll, pitch, yaw = simulate_attitude(t)
        assert -0.3 <= roll <= 0.3
        assert -0.15 <= pitch <= 0.15
        assert 0.0 <= yaw < 2 * math.pi


def test_simulate_position(): 
    lat, lon, alt, head = simulate_position(0.0)
    assert lat == -275969000
    assert lon == -485494000
    assert alt == 10000
    assert head == 0
    lat, lon, alt, head = simulate_position(10.0)
    assert lat == -275968858
    assert lon == -485495989
    assert alt == 8082
    assert head == 5000


def test_simulate_position_ranges():
    for t in [t * 0.1 for t in range(0, 1000)]:
        lat, lon, alt, head = simulate_position(t)
        assert -275970000 <= lat <= -275968000
        assert -485496000 <= lon <= -485494000
        assert 8000 <= alt <= 12000
        assert 0 <= head <= 35999


# ======== send mav messages
def test_send_heartbeat():
    with patch('main.CONN') as mock_conn:
        mock_conn.mav.heartbeat_send = MagicMock()
        send_heartbeat(0)
        mock_conn.mav.heartbeat_send.assert_called_once_with(
            mavutil.mavlink.MAV_TYPE_SUBMARINE,
            mavutil.mavlink.MAV_AUTOPILOT_GENERIC,
            0, 0,
            mavutil.mavlink.MAV_STATE_ACTIVE,
            3
        )


def test_send_attitude():
    with patch('main.CONN') as mock_conn:
        with patch('main.time.time', return_value=10):
            mock_conn.mav.attitude_send = MagicMock()
            send_attitude(0)
            mock_conn.mav.attitude_send.assert_called_once_with(
                10000,
                -0.16320633326681092,
                0.09854798980781836,
                1.0,
                0.0,
                0.0,
                0.0
            )


def test_send_global_position():
    with patch('main.CONN') as mock_conn:
        with patch('main.time.time', return_value=10):
            mock_conn.mav.global_position_int_send = MagicMock()
            send_global_position(0)
            mock_conn.mav.global_position_int_send.assert_called_once_with(
                10000,
                -275968858,
                -485495989,
                8082,
                0,
                0, 0, 0,
                5000
            )
