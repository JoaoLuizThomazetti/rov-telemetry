import asyncio
import zenoh
import time
import json
import threading
from fastapi import FastAPI, WebSocket, Request, Query, HTTPException, status
from fastapi.websockets import WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
from mcap.reader import make_reader
from pydantic import BaseModel


class McapMessage(BaseModel):
    topic: str
    timestamp_us: int
    data: dict


def read_mcap(path, limit: int = 1000) -> list[McapMessage]:
    with open(path, "rb") as f:
        reader = make_reader(f)
        messages = []
        for schema, channel, message in reader.iter_messages():
            if len(messages) >= limit:
                break
            try:
                messages.append(McapMessage(
                    topic=channel.topic,
                    timestamp_us=message.log_time // 1000,
                    data=json.loads(message.data.decode("utf-8")),
                ))
            except Exception as e:
                print(f"erro ao parsear mensagem: {e}")
    return messages


async def broadcast(ws_clients: set[WebSocket], payload: str):
    for client in set(ws_clients):
        await client.send_text(payload)


def subscriber(app: FastAPI, loop: asyncio.AbstractEventLoop):
    session = app.state.zenoh_session

    def on_message(sample):
        payload = bytes(sample.payload).decode("utf-8")
        asyncio.run_coroutine_threadsafe(
            broadcast(app.state.ws_clients, payload),
            loop
        )
    
    session.declare_subscriber("rov/**", on_message)
    while True:
        time.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    session = zenoh.open(zenoh.Config())

    app.state.zenoh_session = session
    app.state.ws_clients = set()
    app.state.mcap_dir = Path("data")

    thread = threading.Thread(
        target=subscriber,
        args=(app, loop),
        daemon=True
    )
    thread.start()

    yield

    session.close()
    for client in app.state.ws_clients:
        await client.close(code=1001)


app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/mcap/files")
async def get_mcap_files(request: Request) -> list[str]:
    mcap_dir = request.app.state.mcap_dir
    return [f.name for f in mcap_dir.glob("*.mcap")]


@app.get("/mcap/messages")
async def get_mcap_messages(request: Request, file: str = Query(...), limit: int = Query(default=1000, le=10000)) -> list[McapMessage]:
    mcap_dir = request.app.state.mcap_dir / file
    if not mcap_dir.resolve().is_relative_to(mcap_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not file.endswith(".mcap"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be .mcap"
        )
    if not mcap_dir.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    try:
        messages = await asyncio.get_running_loop().run_in_executor(None, read_mcap, mcap_dir)
        return messages
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.websocket("/ws/live")
async def ws_connect(ws: WebSocket):
    ws_clients = ws.app.state.ws_clients
    try:
        await ws.accept()
        ws_clients.add(ws)
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ws_clients.discard(ws)
