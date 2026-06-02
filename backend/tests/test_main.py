import time
import json
import pytest
from pathlib import Path
from mcap.writer import Writer
from fastapi import HTTPException
from fastapi.testclient import TestClient
from main import app, check_file, broadcast
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture
def client(tmp_path):
    with patch("zenoh.open", return_value=MagicMock()):
        with TestClient(app) as c:
            c.app.state.mcap_dir = tmp_path
            yield c
        

def fake_mcap(path: Path, corrupt: bool = False) -> dict | None:
    if corrupt:
        with open(path, "wb") as f:
            f.write(b"\x89MCAP0\r\n")
            f.write(b"\xff" * 100)
            return None
    now = int(time.time_ns())
    payload = {
        "system_id": 1,
        "status": "active", 
        "timestamp_us": 1779859720635046
    }

    with open(path, "wb") as f:
        writer = Writer(f)
        writer.start()

        schema_id = writer.register_schema(
            name="heartbeat",
            encoding="jsonschema",
            data=b"{}",
        )

        channel_id = writer.register_channel(
            topic="rov/heartbeat",
            message_encoding="json",
            schema_id=schema_id,
        )

        for _ in range(3):
            writer.add_message(
                channel_id=channel_id,
                log_time=now,
                data=json.dumps(payload).encode(),
                publish_time=now,
            )

        writer.finish()

    return dict(
        topic="rov/heartbeat",
        timestamp_us=now // 1000,
        data=payload
    )


# ======== get all files
def test_get_files_without_mcap(client, tmp_path):
    response = client.get("/mcap/files")
    assert response.status_code == 200
    assert response.json() == []


def test_get_files_with_mcap(client, tmp_path): 
    fake_mcap(tmp_path / "test.mcap")
    response = client.get("/mcap/files")
    assert response.status_code == 200
    assert response.json() == ["test.mcap"]


def test_get_files_corrupted_mcap(client, tmp_path):
    fake_mcap(tmp_path / "test.mcap")
    fake_mcap(tmp_path / "test2.mcap", True)
    response = client.get("/mcap/files")
    assert response.status_code == 200
    assert response.json() == ["test.mcap"]


# ======== download file by name
def test_get_file(client, tmp_path): 
    fake_mcap(tmp_path / "test.mcap")
    response = client.get("/mcap/files/test.mcap")
    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="test.mcap"'
    assert response.headers["content-type"] == "application/octet-stream"
    assert len(response.content) > 0


def test_get_file_not_exist(client, tmp_path): 
    response = client.get("/mcap/files/test.mcap")
    assert response.status_code == 404
    assert response.json()["detail"] ==  "File not found"


# ======== upload file
def test_post_file(client, tmp_path): 
    fake_mcap(tmp_path / "test.mcap")
    with open(tmp_path / "test.mcap", "rb") as f:
        response = client.post("/mcap/files", files={"file": ("testcopy.mcap", f, "application/octet-stream")})
    assert response.status_code == 200
    assert response.json() == {"filename": "testcopy.mcap"}


def test_post_file_already_exists(client, tmp_path): 
    fake_mcap(tmp_path / "test.mcap")
    with open(tmp_path / "test.mcap", "rb") as f:
        response = client.post("/mcap/files", files={"file": ("testcopy.mcap", f, "application/octet-stream")})
    assert response.status_code == 200
    with open(tmp_path / "test.mcap", "rb") as f:
        response = client.post("/mcap/files", files={"file": ("testcopy.mcap", f, "application/octet-stream")})
    assert response.status_code == 409
    assert response.json()["detail"] ==  "File already exists"


def test_post_file_corruptet_mcap(client, tmp_path): 
    fake_mcap(tmp_path / "test.mcap", True)
    with open(tmp_path / "test.mcap", "rb") as f:
        response = client.post("/mcap/files", files={"file": ("testcopy.mcap", f, "application/octet-stream")})
    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid or corrupted mcap file"


# ======== delete file
def test_del_file(client, tmp_path): 
    fake_mcap(tmp_path / "test.mcap")
    response = client.delete("/mcap/files/test.mcap")
    assert response.status_code == 204
    assert not (tmp_path / "test.mcap").exists()


def test_del_file_not_exist(client, tmp_path): 
    response = client.delete("/mcap/files/test.mcap")
    assert response.status_code == 404
    assert response.json()["detail"] ==  "File not found"


# ======== get messages
def test_get_messages_invalid_ext(client, tmp_path):
    response = client.get("/mcap/messages/test.mp4")
    assert response.status_code == 400
    assert response.json()["detail"] == "File must be .mcap"


def test_get_messages_file_not_found(client, tmp_path):
    response = client.get("/mcap/messages/test.mcap")
    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_get_messages_reading_mcap(client, tmp_path):
    payload = fake_mcap(tmp_path / "test.mcap")
    response = client.get("/mcap/messages/test.mcap")
    assert response.status_code == 200
    assert response.json() == [payload, payload, payload]


def test_get_messages_with_limit(client, tmp_path):
    payload = fake_mcap(tmp_path / "test.mcap")
    response = client.get("/mcap/messages/test.mcap?limit=1")
    assert response.status_code == 200
    assert response.json() == [payload]


@pytest.mark.asyncio
async def test_get_messages_invalid_path(tmp_path):
    with pytest.raises(HTTPException) as exc:
        await check_file(tmp_path, "../test.mcap")
    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid path"


# ======== websocket connection
def test_websocket_register_client(client):
    with client.websocket_connect("/ws/live") as ws:
        assert len(client.app.state.ws_clients) == 1
    assert len(client.app.state.ws_clients) == 0


@pytest.mark.asyncio
async def test_websocket_broadcast():
    ws_client_1 = MagicMock()
    ws_client_1.send_text = AsyncMock()
    ws_client_2 = MagicMock()
    ws_client_2.send_text = AsyncMock(side_effect=Exception("disconnected"))
    ws_clients = set()
    ws_clients.add(ws_client_1) 
    ws_clients.add(ws_client_2)
    await broadcast(ws_clients, '{"topic": "test"}')
    ws_client_1.send_text.assert_called_once_with('{"topic": "test"}')
    assert ws_clients == {ws_client_1}
