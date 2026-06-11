import os
import time
import math
import asyncio
import serial_asyncio
import serial.tools.list_ports
from fastapi import (
    FastAPI,
    Request,
    HTTPException,
    status
)
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pydantic import BaseModel, Field
from typing import Callable, Coroutine
from pymavlink import mavutil
from pymavlink.dialects.v20 import ardupilotmega as mav
from dataclasses import dataclass, field


SYS_ID = 1
COMP_ID = 1
TARGET = os.getenv('MAVLINK_TARGET', 'udpout:127.0.0.1:14550')
BOOT_TIME = int(time.time() * 1000)
CONN = None
BAUD_RATE = 57600


SENSORS = (
    mav.MAV_SYS_STATUS_SENSOR_3D_GYRO
    | mav.MAV_SYS_STATUS_SENSOR_3D_ACCEL
    | mav.MAV_SYS_STATUS_SENSOR_3D_MAG
    | mav.MAV_SYS_STATUS_SENSOR_ABSOLUTE_PRESSURE
    | mav.MAV_SYS_STATUS_SENSOR_GPS
)


@dataclass
class Task:
    fn: Callable
    interval: float
    last: float = field(default_factory=time.monotonic)


@dataclass
class ManagedTask:
    name: str
    coroutine_fn: Callable[..., Coroutine]
    _task: asyncio.Task | None = field(default=None, repr=False)

    def start(self, *args, **kwargs) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self.coroutine_fn(*args, **kwargs))
        self._task.set_name(self.name)

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()


class StatusResponse(BaseModel):
    source: str | None = Field(default=None, description="MAVLink source")
    port: str | None = Field(default=None, description="USB port")
    running: bool = Field(default=False, description="UDP transmitting")


def get_conn():
    global CONN
    if CONN is None:
        CONN = mavutil.mavlink_connection(TARGET, source_system=1)
    return CONN


def elapsed_ms() -> int:
    return (int(time.time() * 1000) - BOOT_TIME) & 0xFFFFFFFF


def elapsed_s() -> float:
    return elapsed_ms() / 1000.0


def sim_roll() -> float:
    return 0.05 * math.sin(elapsed_s() * 0.5)


def sim_pitch() -> float:
    return 0.03 * math.sin(elapsed_s() * 0.7)


def sim_yaw() -> float:
    return math.fmod(elapsed_s() * 0.1, math.tau)


def sim_depth() -> float:
    return 2.0 + 1.5 * math.sin(elapsed_s() * 0.2)


def sim_speed() -> float:
    return 0.5 + 0.3 * math.sin(elapsed_s() * 0.3)


def sim_batt() -> int:
    return max(0, 100 - int(elapsed_s() / 10))


def send_heartbeat() -> None:
    get_conn().mav.heartbeat_send(
        mav.MAV_TYPE_SUBMARINE,
        mav.MAV_AUTOPILOT_ARDUPILOTMEGA,
        mav.MAV_MODE_FLAG_STABILIZE_ENABLED | mav.MAV_MODE_FLAG_SAFETY_ARMED,
        0,
        mav.MAV_STATE_ACTIVE,
    )


def send_sys_status() -> None:
    get_conn().mav.sys_status_send(
        SENSORS,
        SENSORS,
        SENSORS,
        300,
        14800,
        2500,
        sim_batt(),
        0, 0,
        0, 0, 0, 0,
    )


def send_attitude() -> None:
    ts = elapsed_s()
    get_conn().mav.attitude_send(
        elapsed_ms(),
        sim_roll(),
        sim_pitch(),
        sim_yaw(),
        0.02 * math.cos(ts),
        0.01 * math.cos(ts * 0.7),
        0.01,
    )


def send_global_position() -> None:
    ts = elapsed_s()
    lat = int((-27.5969 + 0.0001 * math.sin(ts * 0.3)) * 1e7)
    lon = int((-48.5495 + 0.0001 * math.cos(ts * 0.3)) * 1e7)
    alt = int(-sim_depth() * 1000)
    hdg = int(math.fmod(ts * 5.0, 360.0) * 100)
    get_conn().mav.global_position_int_send(
        elapsed_ms(),
        lat,
        lon,
        alt,
        0,
        0, 0, 0,
        hdg,
    )


def send_scaled_pressure2() -> None:
    press_abs = 1013.25 + sim_depth() * 9.8
    get_conn().mav.scaled_pressure2_send(
        elapsed_ms(),
        press_abs,
        0.0,
        2000,
    )


def send_battery_status() -> None:
    cells = [3750, 3700, 3680, 3670] + [65535] * 6
    get_conn().mav.battery_status_send(
        0,
        mav.MAV_BATTERY_FUNCTION_ALL,
        mav.MAV_BATTERY_TYPE_LIPO,
        2000,
        cells,
        2500,
        -1,
        -1,
        sim_batt(),
    )


def send_vfr_hud() -> None:
    ts = elapsed_s()
    get_conn().mav.vfr_hud_send(
        sim_speed(),
        sim_speed() * 0.9,
        int(math.fmod(ts * 5.0, 360.0)),
        int(30 + 20 * math.sin(ts * 0.3)),
        -sim_depth(),
        0.05 * math.cos(ts * 0.4),
    )


def send_statustext(text: str, severity: int = mav.MAV_SEVERITY_INFO) -> None:
    get_conn().mav.statustext_send(
        severity,
        text.encode(),
    )


async def test_if_mavlink(port: str, baud: int, timeout: float = 2.0) -> bool:
    try:
        conn = mavutil.mavlink_connection(port, baud=baud)
        msg = await asyncio.get_running_loop().run_in_executor(None, lambda: conn.recv_match(type="HEARTBEAT", blocking=True, timeout=timeout))
        conn.close()
        return msg is not None
    except Exception:
        return False


async def run_simulation(tasks: list[Task]) -> None:
    while True:
        now = time.monotonic()
        for task in tasks:
            if now - task.last >= task.interval:
                try:
                    task.fn()
                    task.last = now
                except Exception as e:
                    print(f"[simulator] {task.fn.__name__} failed: {e}")
        await asyncio.sleep(0.01)


async def run_serial_proxy(port: str, baud: int) -> None:
    reader, writer = await serial_asyncio.open_serial_connection(url=port, baudrate=baud)
    conn = get_conn()
    try:
        while True:
            data = await reader.read(256)
            if data:
                conn.write(data)
    finally:
        writer.close()
        await writer.wait_closed()


TASKS = [
    Task(fn=send_heartbeat, interval=1.0),
    Task(fn=send_sys_status, interval=1.0),
    Task(fn=send_attitude, interval=0.1),
    Task(fn=send_global_position, interval=0.1),
    Task(fn=send_vfr_hud, interval=0.1),
    Task(fn=send_scaled_pressure2, interval=0.5),
    Task(fn=send_battery_status, interval=1.0),
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    send_statustext("BlueROV2 simulator started", mav.MAV_SEVERITY_INFO)
    app.state.simulation = ManagedTask("simulator", run_simulation)
    app.state.serial_proxy = ManagedTask("serial-proxy", run_serial_proxy)
    app.state.source = None
    app.state.port = None
    app.state.running = False
    yield


app = FastAPI(
    title="ROV Simulator",
    description="MAVLink simulator and serial proxy",
    version="1.0.0",
    lifespan=lifespan,
    root_path="/simulator",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health", tags=["HEALTH"])
async def get_health():
    """Health check"""
    return {"status": "ok"}


@app.get("/status", tags=["MAVLINK"], responses={
    500: {"description": "Internal server error"}
})
async def get_status(request: Request) -> StatusResponse:
    """Get current service status"""
    return StatusResponse (
        source = request.app.state.source,
        port = request.app.state.port,
        running = request.app.state.running
    )


@app.get("/ports", tags=["MAVLINK"], responses={
    500: {"description": "Internal server error"}
})
async def get_ports() -> list[str]:
    """List available serial ports with mavlink devices"""
    ports = []
    available_ports = serial.tools.list_ports.comports()
    for port in available_ports:
        if await test_if_mavlink(port.device, BAUD_RATE):
            ports.append(port.device)
    return ports


@app.post("/start", tags=["MAVLINK"], responses={
    404: {"description": "Source not found"},
    500: {"description": "Internal server error"},
})
async def start_simulator(request: Request, source: str, port: str | None = None) -> StatusResponse:
    """Start MAVLink transmission"""
    match source:
        case 'simulation':
            if request.app.state.serial_proxy.running: request.app.state.serial_proxy.stop()
            for task in TASKS:
                task.last = time.monotonic()
            request.app.state.simulation.start(TASKS)
            request.app.state.source = 'simulation'
            request.app.state.port = None
        case 'serial':
            if request.app.state.simulation.running: request.app.state.simulation.stop()
            request.app.state.serial_proxy.start(port, BAUD_RATE)
            request.app.state.source = 'serial'
            request.app.state.port = port
        case _:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    request.app.state.running = True
    return StatusResponse (
        source = request.app.state.source,
        port = request.app.state.port,
        running = request.app.state.running
    )


@app.post("/stop", tags=["MAVLINK"], responses={
    404: {"description": "Source not found"},
    500: {"description": "Internal server error"},
})
async def stop_simulator(request: Request, source: str) -> StatusResponse:
    """Stop MAVLink transmission"""
    match source:
        case 'simulation':
            request.app.state.simulation.stop()
        case 'serial':
            request.app.state.serial_proxy.stop()
        case _:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    request.app.state.source = None
    request.app.state.port = None
    request.app.state.running = False
    return StatusResponse (
        source = request.app.state.source,
        port = request.app.state.port,
        running = request.app.state.running
    )
