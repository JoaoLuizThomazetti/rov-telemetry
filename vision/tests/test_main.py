import pytest
from main import app
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    with TestClient(app) as c:
        app.state.video_dir = tmp_path
        app.state.peer_conns = set()
        yield c


# ======== Health check
def test_get_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ======== Video sources
def test_get_sources(client):
    with patch("main.cv2.VideoCapture") as mock_cap:
        mock_cap.return_value.isOpened.return_value = False
        response = client.get("/sources")
        assert response.status_code == 200
        assert response.json() ==  {'cameras': [], 'videos': []}


def test_get_sources_with_files(client):
    video_dir = app.state.video_dir
    with patch("main.cv2.VideoCapture") as mock_cap:
        mock_cap.return_value.isOpened.return_value = False
        with open((video_dir / "test.mp4"), "wb") as file:
            file.write(b"test")
        response = client.get("/sources")
        assert response.status_code == 200
        assert response.json() == {'cameras': [], 'videos': ["test.mp4"]}


# ======== Upload video
def test_post_video(client):
    video_dir = app.state.video_dir
    with patch("main.test_video", return_value=True):
        with open((video_dir / "test.mp4"), "wb") as file:
            file.write(b"test")
        with open(video_dir / "test.mp4", "rb") as file:
            response = client.post("/videos", files={"file": ("testUpload.mp4", file, "application/octet-stream")})
        assert response.status_code == 200
        assert response.json() == {"filename": "testUpload.mp4"}


def test_post_video_wrong_ext(client):
    video_dir = app.state.video_dir
    with patch("main.test_video", return_value=True):
        with open((video_dir / "test.mp3"), "wb") as file:
            file.write(b"test")
        with open(video_dir / "test.mp3", "rb") as file:
            response = client.post("/videos", files={"file": ("testUpload.mp3", file, "application/octet-stream")})
        assert response.status_code == 400
        assert response.json()["detail"] == "File must be .mp4"


def test_post_video_already_exist(client):
    video_dir = app.state.video_dir
    with patch("main.test_video", return_value=True):
        with open((video_dir / "test.mp4"), "wb") as file:
            file.write(b"test")
        with open(video_dir / "test.mp4", "rb") as file:
            response = client.post("/videos", files={"file": ("test.mp4", file, "application/octet-stream")})
        assert response.status_code == 409
        assert response.json()["detail"] == "File already exists"


def test_post_video_corrupted(client):
    video_dir = app.state.video_dir
    with open((video_dir / "test.mp4"), "wb") as file:
        file.write(b"")
    with open(video_dir / "test.mp4", "rb") as file:
        response = client.post("/videos", files={"file": ("testPost.mp4", file, "application/octet-stream")})
    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid or corrupted video file"


# ======== Delete video
def test_del_video(client):
    video_dir = app.state.video_dir
    with patch("main.test_video", return_value=True):
        with open((video_dir / "test.mp4"), "wb") as file:
            file.write(b"test")
        response = client.delete("/videos/test.mp4")
        assert response.status_code == 204


def test_del_video_not_exist(client):
    response = client.delete("/videos/test.mp4")
    assert response.status_code == 404
