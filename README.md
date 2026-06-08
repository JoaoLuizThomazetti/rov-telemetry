# ROV Telemetry

Real-time telemetry dashboard for ROV (Remotely Operated Vehicle) data.

![screenshot](https://github.com/user-attachments/assets/e95326ca-7fc3-49c2-b646-c1080233bea9)

<video src="https://github.com/user-attachments/assets/6514db3f-b954-42c5-8ef8-232900649967" controls width="100%"></video>

---

## Architecture

Six independent services + zenoh router:

- **mavlink-simulator:** Python + pymavlink | Publishes synthetic ROV telemetry as MAVLink UDP at 10Hz
- **mavlink-bridge:** Rust + Zenoh | Receives MAVLink, decodes messages, publishes to Zenoh topics
- **recorder:** Rust + Axum + Zenoh | Subscribes to all topics, writes MCAP files on demand
- **backend:** Python + FastAPI + Zenoh | Reads MCAP files, forwards live data via WebSocket
- **vision:** Python + FastAPI + aiortc + OpenCV | WebRTC video streaming from cameras and video files
- **frontend:** Vue 3 + Vuetify + Vite | Live telemetry, MCAP replay, and WebRTC video stream UI
- **zenoh-router:** Eclipse Zenoh | Message broker for all inter-service communication

---

## Features

### Live Mode
- Real-time telemetry via WebSocket: Heartbeat, Attitude (roll/pitch/yaw), GPS Position
- Connection status indicator with auto-reconnect

### Replay Mode
- Upload, download, and delete MCAP recording files
- Load recordings with configurable message limit
- Time slider for scrubbing through recorded data

### Recording
- Start/stop MCAP recordings via REST API (`POST /recorder/start`, `POST /recorder/stop`)
- Graceful shutdown (SIGTERM handler) ensures files are always properly finalized
- Tolerant reader: partial recordings from interrupted sessions are listed when readable

### Video Streaming
- WebRTC peer-to-peer video stream from physical cameras or uploaded `.mp4` files
- Upload and delete video files via the UI
- Optional TURN server support for remote deployments (configurable via environment variables)
- Optional real-time YOLO object detection overlay (YOLOv8n fine-tuned on underwater marine species: eel, fish, jellyfish, lionfish, lobster — mAP50 80.6%)

---

## Running locally

```bash
docker compose up --build
```

Frontend available at `http://localhost`.

---

## CI/CD

Push to `main` triggers a GitHub Actions workflow that:
1. Builds all 5 Docker images in parallel
2. Pushes to GitHub Container Registry (`ghcr.io`)
3. Deploys to VPS via SSH

```bash
# Production deploy (VPS)
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

---

## Recorder API

| Method | Path | Description |
|---|---|---|
| `POST` | `/recorder/start` | Start a new MCAP recording |
| `POST` | `/recorder/stop` | Stop and finalize the current recording |
| `GET` | `/recorder/status` | Recording status, filename, start time |

## Vision API

| Method | Path | Description |
|---|---|---|
| `GET` | `/vision/sources` | List available cameras and video files |
| `POST` | `/vision/offer` | Exchange WebRTC SDP offer/answer |
| `POST` | `/vision/videos` | Upload a `.mp4` video file |
| `DELETE` | `/vision/videos/{filename}` | Delete a video file |
