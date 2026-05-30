import os
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
from mcap.reader import NonSeekingReader
from pydantic import BaseModel


MCAP_DIR = Path(os.environ.get("MCAP_DIR", "."))


class McapMessage(BaseModel):
    topic: str
    timestamp_us: int
    data: dict


def read_mcap(path: Path, limit: int = 1000) -> list[McapMessage]:
      messages = []
      try:
          with open(path, "rb") as f:
              reader = NonSeekingReader(f)
              for schema, channel, message in reader.iter_messages():
                  if len(messages) >= limit:
                      break
                  try:
                      messages.append(McapMessage(
                          topic=channel.topic,
                          timestamp_us=message.log_time // 1000,
                          data=json.loads(message.data.decode("utf-8")),
                      ))
                  except Exception:
                      pass
      except Exception:
          pass
      return messages


async def broadcast(ws_clients: set[WebSocket], payload: str):
    for client in set(ws_clients):
        await client.send_text(payload)


def subscriber(app: FastAPI, loop: asyncio.AbstractEventLoop):
    session = app.state.zenoh_session

    def on_message(sample):
        payload = json.dumps({
            "topic": str(sample.key_expr),
            "data": json.loads(bytes(sample.payload).decode("utf-8")),
        })
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

    connect = os.environ.get("ZENOH_CONNECT", "tcp/localhost:7447")
    config = zenoh.Config()
    config.insert_json5("mode", '"client"')
    config.insert_json5("connect/endpoints", f'["{connect}"]')
    session = zenoh.open(config)

    app.state.zenoh_session = session
    app.state.ws_clients = set()
    app.state.mcap_dir = Path(MCAP_DIR)

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


app = FastAPI(lifespan=lifespan, root_path="/mcap")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/files")
async def get_mcap_files(request: Request) -> list[str]:
    mcap_dir = request.app.state.mcap_dir
    return [f.name for f in mcap_dir.glob("*.mcap")]


@app.get("/messages")
async def get_mcap_messages(request: Request, file: str = Query(...), limit: int = Query(default=1000, le=10000)) -> list[McapMessage]:
    mcap_dir = request.app.state.mcap_dir
    file_path = (mcap_dir / file).resolve()
    if not file_path.is_relative_to(mcap_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not file.endswith(".mcap"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be .mcap"
        )
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    try:
        messages = await asyncio.get_running_loop().run_in_executor(None, read_mcap, file_path, limit)
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
