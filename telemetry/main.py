import json
import docker
import psutil
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pydantic import BaseModel
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, WebSocket
from fastapi.websockets import WebSocketDisconnect
from fastapi.responses import JSONResponse
from helpers import logger


_docker_client = docker.from_env()


class SystemData(BaseModel):
    cpu_percent: float
    mem_percent: float
    disk_percent: float


class ContainerData(BaseModel):
    name: str
    status: str
    uptime_s: int


@dataclass
class ResourcesState:
    system: SystemData | None = None
    containers: list[ContainerData] = field(default_factory=list)


def gather_data() -> tuple[SystemData, list[ContainerData]]:
    system = SystemData(
        cpu_percent=psutil.cpu_percent(interval=1),
        mem_percent=psutil.virtual_memory().percent,
        disk_percent=psutil.disk_usage("/").percent,
    )
    containers = []
    for container in _docker_client.containers.list(all=True):
        if not container.name.startswith("rov-telemetry"):
            continue
        uptime_s = 0
        if container.status == "running":
            started_at = container.attrs["State"]["StartedAt"]
            started_at = started_at[:26] + "+00:00"
            started_dt = datetime.fromisoformat(started_at)
            uptime_s = int((datetime.now(timezone.utc) - started_dt).total_seconds())
        containers.append(ContainerData(
            name=container.name.replace("rov-telemetry-", "")[:-2],
            status=container.status,
            uptime_s=uptime_s
        ))
    return system, containers


async def broadcast(ws_clients: set[WebSocket], payload: str) -> None:
    for client in set(ws_clients):
        try:
            await client.send_text(payload)
        except Exception:
            ws_clients.discard(client)


async def loop_system_info(app: FastAPI) -> None:
    logger.info("Starting system info loop")
    while True:
        try:
            system, containers = await asyncio.to_thread(gather_data)
            app.state.resources.system = system
            app.state.resources.containers = containers
            payload = json.dumps({
                "system": system.model_dump(),
                "containers": [c.model_dump() for c in containers],
            })
            await broadcast(app.state.ws_clients, payload)
        except Exception as e:
            logger.exception(f"Failed to retrieve system resources: {e}")
        await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting Overseer")
    app.state.ws_clients = set()
    app.state.resources = ResourcesState()
    task = asyncio.create_task(loop_system_info(app))
    yield
    logger.info("Stopping Overseer")
    task.cancel()


app = FastAPI(
    title="Telemetry API",
    description="System and docker monitor",
    lifespan=lifespan,
    version="1.0.0",
    root_path="/telemetry",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"ERROR: {request.url.path}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/system", tags=["OVERSEER"], responses={
    500: {"description": "Server error"},
})
async def get_system_status(request: Request) -> SystemData:
    """Get system status."""
    resources = request.app.state.resources
    return resources.system


@app.get("/containers", tags=["OVERSEER"], responses={
    500: {"description": "Server error"},
})
async def get_container_status(request: Request) -> list[ContainerData]:
    """Get container status."""
    resources = request.app.state.resources
    return resources.containers


@app.websocket("/ws/live")
async def ws_connect(ws: WebSocket):
    ws_clients = ws.app.state.ws_clients
    try:
        await ws.accept()
        ws_clients.add(ws)
        logger.info(f"Websocket connected (clients={len(ws_clients)})")
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        logger.info(f"Websocket disconnected")
        pass
    except Exception as e:
        logger.exception(f"Websocket conn error: {e}")
    finally:
        ws_clients.discard(ws)
