# ROV Telemetry

Real-time telemetry dashboard for ROV (Remotely Operated Vehicle) data.

**demo:** https://rov-telemetry.jlconsultoria.dev.br (user: `rov` / pass: `mcap`)

---

## Architecture

Five independent services communicating via [Zenoh](https://zenoh.io/) pub/sub:


**simulator:** Rust + Zenoh | Publishes synthetic ROV telemetry at 10Hz
**recorder:** Rust + Axum + Zenoh | Subscribes to all topics, writes MCAP files on demand
**backend:** Python + FastAPI + Zenoh | Reads MCAP files, forwards live data via WebSocket
**frontend:** Vue 3 + Vuetify + Vite | Live telemetry display and MCAP replay UI
**zenoh-router:** Eclipse Zenoh | Message broker for all inter-service communication

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

---

## Running locally

```bash
docker compose up --build
```

Frontend available at `http://localhost`.

---

## CI/CD

Push to `main` triggers a GitHub Actions workflow that:
1. Builds all 4 Docker images in parallel
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
