import sys
import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

sys.modules["helpers"] = MagicMock()
sys.modules["docker"] = MagicMock()

from fastapi.testclient import TestClient
from main import app, gather_data, broadcast, SystemData, ContainerData


@pytest.fixture
def client():
    system = SystemData(
        cpu_percent=1.0,
        mem_percent=2.0,
        disk_percent=3.0
    )
    containers = [
        ContainerData(name="backend", status="running", uptime_s=300),
        ContainerData(name="vision", status="exited", uptime_s=0),
    ]
    with patch("main.gather_data", return_value=(system, containers)):
        with TestClient(app) as client:
            yield client


def test_get_system_fields(client):
    response = client.get("/system")
    assert response.status_code == 200
    data = response.json()
    assert "cpu_percent" in data
    assert "mem_percent" in data
    assert "disk_percent" in data


def test_get_system_values(client):
    response = client.get("/system")
    assert response.status_code == 200
    data = response.json()
    assert data["cpu_percent"] == 1.0
    assert data["mem_percent"] == 2.0
    assert data["disk_percent"] == 3.0


def test_get_containers_return(client):
    response = client.get("/containers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(response.json(), list)
    assert len(data) == 2
    assert data[0]["name"] == "backend"
    assert data[0]["status"] == "running"
    assert data[1]["name"] == "vision"
    assert data[1]["status"] == "exited"


def test_get_containers_empty(client):
    client.app.state.resources.containers = []
    response = client.get("/containers")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_broadcast():
    ws1 = MagicMock()
    ws1.send_text = AsyncMock()
    ws2 = MagicMock()
    ws2.send_text = AsyncMock()
    clients = {ws1, ws2}
    await broadcast(clients, '{"test": true}')
    ws1.send_text.assert_called_once_with('{"test": true}')
    ws2.send_text.assert_called_once_with('{"test": true}')


def test_gather_data_system_fields():
    with (
        patch("main.psutil.cpu_percent") as mock_cpu,
        patch("main.psutil.virtual_memory") as mock_memory,
        patch("main.psutil.disk_usage") as mock_disk,
        patch("main._docker_client") as mock_containers
    ):
        mock_cpu.return_value = 4.0
        mock_memory.return_value.percent = 5.0
        mock_disk.return_value.percent = 6.0
        mock_containers.containers.list.return_value = []
        system, _ = gather_data()
    assert system.cpu_percent == 4.0
    assert system.mem_percent == 5.0
    assert system.disk_percent == 6.0


def test_gather_data_filter_containers():
    valid_container = MagicMock()
    valid_container.name = "rov-telemetry-backend-1"
    valid_container.status = "exited"
    another_container = MagicMock()
    another_container.name = "unrelated-nginx"
    with (
        patch("main.psutil.cpu_percent") as mock_cpu,
        patch("main.psutil.virtual_memory") as mock_memory,
        patch("main.psutil.disk_usage") as mock_disk,
        patch("main._docker_client") as mock_containers
    ):
        mock_cpu.return_value = 0.0
        mock_memory.return_value.percent = 0.0
        mock_disk.return_value.percent = 0.0
        mock_containers.containers.list.return_value = [valid_container, another_container]
        _, containers = gather_data()
    assert len(containers) == 1
    assert containers[0].name == "backend"
    assert containers[0].status == "exited"


def test_websocket_register_client(client):
    with client.websocket_connect("/ws/live") as ws:
        assert len(client.app.state.ws_clients) == 1
    assert len(client.app.state.ws_clients) == 0
