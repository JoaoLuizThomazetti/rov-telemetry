# ROV Telemetry

Real-time telemetry dashboard for ROV (Remotely Operated Vehicle) data.

<img width="1843" height="1077" alt="Image" src="https://github.com/user-attachments/assets/732618eb-2332-4876-b3b9-2926bedc7533" />

<video src="https://github.com/user-attachments/assets/cc36b317-5e2e-403d-9aac-1353dd43d19d" controls width="100%"></video>

---

## Architecture

Seven independent services + zenoh router:

- **mavlink-simulator:** Python + FastAPI + pymavlink | Software MAVLink simulator or serial proxy for real hardware (ESP32/ArduPilot)
- **mavlink-bridge:** Rust + Zenoh | Receives MAVLink UDP, decodes messages, publishes to Zenoh topics
- **recorder:** Rust + Axum + Zenoh | Subscribes to all topics, writes MCAP files on demand
- **backend:** Python + FastAPI + Zenoh | Reads MCAP files, forwards live data via WebSocket
- **vision:** Python + FastAPI + aiortc + OpenCV | WebRTC video streaming from cameras and video files
- **frontend:** Vue 3 + Vuetify + Vite | Live telemetry, MCAP replay, WebRTC video stream, and simulator control UI
- **zenoh-router:** Eclipse Zenoh | Message broker for all inter-service communication

---

## Features

### Live Mode
- Real-time telemetry via WebSocket: Heartbeat, Attitude (roll/pitch/yaw), GPS Position
- Connection status indicator with auto-reconnect
- MAVLink source selector: software simulation or physical serial device (ESP32/ArduPilot)

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
- Optional real-time YOLO object detection overlay — YOLOv8n fine-tuned on the [Underwater Marine Species dataset](https://universe.roboflow.com/california-state-university-east-bay/underwater-marine-species) by California State University East Bay (eel, fish, jellyfish, lionfish, lobster — mAP50 80.6%)

### ESP32 Firmware
- MAVLink firmware for ESP32 (`esp32-mavlink/`) sending HEARTBEAT, ATTITUDE, GLOBAL_POSITION_INT, SYS_STATUS, BATTERY_STATUS, SCALED_PRESSURE2, and VFR_HUD at configurable rates
- Built with PlatformIO + Arduino framework; MAVLink C library v2 included

---

## Running locally

```bash
docker compose up --build
```

Frontend available at `http://localhost`.

To flash the ESP32 firmware:
```bash
cd esp32-mavlink && uv run pio run --target upload
```

---

## CI/CD

Push to `main` triggers a GitHub Actions workflow that:
1. Runs Python and Rust test suites
2. Builds all Docker images in parallel
3. Pushes to GitHub Container Registry (`ghcr.io`)
4. Deploys to VPS via SSH

```bash
# Production deploy (VPS)
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

---

## Simulator API

| Method | Path | Description |
|---|---|---|
| `GET` | `/simulator/status` | Current source, port, and running state |
| `GET` | `/simulator/ports` | List serial ports with active MAVLink devices |
| `POST` | `/simulator/start?source=simulation` | Start software MAVLink simulation |
| `POST` | `/simulator/start?source=serial&port=/dev/ttyUSB0` | Start serial proxy from hardware device |
| `POST` | `/simulator/stop` | Stop active transmission |

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
