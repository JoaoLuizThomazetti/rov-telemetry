import math
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from main import app, sim_roll, sim_pitch, sim_yaw, sim_depth, sim_speed, sim_batt, TASKS


@pytest.fixture
def client():
    app.state.simulation = MagicMock()
    app.state.serial_proxy = MagicMock()
    app.state.source = None
    app.state.port = None
    app.state.running = False
    with patch("main.get_conn"):
        yield TestClient(app)


def test_sim_roll_range():
    with patch("main.BOOT_TIME", 0):
        for t in range(0, 100):
            with patch("main.time.time", return_value=float(t)):
                assert -0.05 <= sim_roll() <= 0.05


def test_sim_pitch_range():
    with patch("main.BOOT_TIME", 0):
        for t in range(0, 100):
            with patch("main.time.time", return_value=float(t)):
                assert -0.03 <= sim_pitch() <= 0.03


def test_sim_yaw_wraps():
    with patch("main.BOOT_TIME", 0):
        for t in range(0, 100):
            with patch("main.time.time", return_value=float(t)):
                assert 0.0 <= sim_yaw() < math.tau


def test_sim_depth_range():
    with patch("main.BOOT_TIME", 0):
        for t in range(0, 100):
            with patch("main.time.time", return_value=float(t)):
                assert 0.5 <= sim_depth() <= 3.5


def test_sim_speed_range():
    with patch("main.BOOT_TIME", 0):
        for t in range(0, 100):
            with patch("main.time.time", return_value=float(t)):
                assert 0.2 <= sim_speed() <= 0.8


def test_sim_batt_decreases():
    with patch("main.BOOT_TIME", 0):
        with patch("main.time.time", return_value=0.0):
            b0 = sim_batt()
        with patch("main.time.time", return_value=200.0):
            b1 = sim_batt()
    assert b1 < b0


def test_sim_batt_never_negative():
    with patch("main.BOOT_TIME", 0):
        with patch("main.time.time", return_value=1e7):
            assert sim_batt() >= 0


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_status_initial_state(client):
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["running"] == False
    assert data["source"] is None
    assert data["port"] is None


def test_status_after_start(client):
    client.post("/start?source=simulation")
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["running"] == True
    assert data["source"] == "simulation"


def test_ports_no_devices(client):
    with patch("main.serial.tools.list_ports.comports", return_value=[]):
        response = client.get("/ports")
        assert response.status_code == 200
        assert response.json() == []


def test_ports_with_mavlink_device(client):
    mock_port = MagicMock()
    mock_port.device = "/dev/ttyUSB0"
    with patch("main.serial.tools.list_ports.comports", return_value=[mock_port]):
        with patch("main.test_if_mavlink", new_callable=AsyncMock, return_value=True):
            response = client.get("/ports")
            assert response.status_code == 200
            assert "/dev/ttyUSB0" in response.json()


def test_ports_device_without_mavlink(client):
    mock_port = MagicMock()
    mock_port.device = "/dev/ttyUSB0"
    with patch("main.serial.tools.list_ports.comports", return_value=[mock_port]):
        with patch("main.test_if_mavlink", new_callable=AsyncMock, return_value=False):
            response = client.get("/ports")
            assert response.status_code == 200
            assert response.json() == []


def test_start_simulation(client):
    response = client.post("/start?source=simulation")
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "simulation"
    assert data["running"] == True
    assert data["port"] is None
    app.state.simulation.start.assert_called_once_with(TASKS)


def test_start_serial(client):
    response = client.post("/start?source=serial&port=/dev/ttyUSB0")
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "serial"
    assert data["port"] == "/dev/ttyUSB0"
    assert data["running"] == True
    app.state.serial_proxy.start.assert_called_once()


def test_start_invalid_source(client):
    response = client.post("/start?source=invalid")
    assert response.status_code == 404
    assert response.json()["detail"] == "Source not found"


def test_start_simulation_stops_serial(client):
    app.state.serial_proxy.running = True
    client.post("/start?source=simulation")
    app.state.serial_proxy.stop.assert_called_once()


def test_start_serial_stops_simulation(client):
    app.state.simulation.running = True
    client.post("/start?source=serial&port=/dev/ttyUSB0")
    app.state.simulation.stop.assert_called_once()


def test_stop_simulation(client):
    app.state.source = "simulation"
    app.state.running = True
    response = client.post("/stop?source=simulation")
    assert response.status_code == 200
    data = response.json()
    assert data["running"] == False
    assert data["source"] is None
    assert data["port"] is None
    app.state.simulation.stop.assert_called_once()


def test_stop_serial(client):
    app.state.source = "serial"
    app.state.port = "/dev/ttyUSB0"
    app.state.running = True
    response = client.post("/stop?source=serial")
    assert response.status_code == 200
    data = response.json()
    assert data["running"] == False
    app.state.serial_proxy.stop.assert_called_once()


def test_stop_invalid_source(client):
    response = client.post("/stop?source=invalid")
    assert response.status_code == 404
    assert response.json()["detail"] == "Source not found"
