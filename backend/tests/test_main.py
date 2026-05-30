import pytest
import time
import json
from pathlib import Path
from mcap.writer import Writer
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client(tmp_path):
    with patch("zenoh.open", return_value=MagicMock()):
        with TestClient(app) as c:
            c.app.state.mcap_dir = tmp_path
            yield c
        

def fake_mcap(path: Path) -> dict:
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


# ======== download file by name
def test_get_file(client, tmp_path): 
    fake_mcap(tmp_path / "test.mcap")
    response = client.get("/mcap/files/test.mcap")
    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="test.mcap"'
    assert response.headers["content-type"] == "application/octet-stream"
    assert len(response.content) > 0


# ======== upload file
def test_post_file(client, tmp_path): 
    fake_mcap(tmp_path / "test.mcap")
    with open(tmp_path / "test.mcap", "rb") as f:
        response = client.post("/mcap/files", files={"file": ("testcopy.mcap", f, "application/octet-stream")})
    assert response.status_code == 200
    assert response.json() == {"filename": "testcopy.mcap"}


# ======== delete file
def test_del_file(client, tmp_path): 
    fake_mcap(tmp_path / "test.mcap")
    response = client.delete("/mcap/files/test.mcap")
    assert response.status_code == 204
    assert not (tmp_path / "test.mcap").exists()


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
    assert response.json() == [payload]


# ======== websocket connect
def test_websocket_connects(client):
    with client.websocket_connect("/ws/live") as ws:
        pass
