import os
import asyncio
import zenoh
import time
import json
import threading
import shutil
from fastapi import (
    FastAPI,
    WebSocket,
    Request,
    Response,
    Query,
    HTTPException,
    status,
    UploadFile,
    File
)
from fastapi.responses import FileResponse
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
    with open(path, "rb") as f:
        reader = NonSeekingReader(f)
        try:
            for schema, channel, message in reader.iter_messages():
                if len(messages) >= limit:
                    break
                messages.append(McapMessage(
                    topic=channel.topic,
                    timestamp_us=message.log_time // 1000,
                    data=json.loads(message.data.decode("utf-8")),
                ))
        except Exception:
            pass
    return messages


async def broadcast(ws_clients: set[WebSocket], payload: str):
    for client in set(ws_clients):
        try:
            await client.send_text(payload)
        except Exception:
            ws_clients.discard(client)


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


async def check_file(mcap_dir: Path, file_name: str, is_upload: bool = False):
    if not file_name.endswith(".mcap"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be .mcap")
    if not (mcap_dir / file_name).resolve().is_relative_to(mcap_dir.resolve()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")
    if is_upload:
        if (mcap_dir / file_name).resolve().exists():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="File already exists")
    else:
        if not (mcap_dir / file_name).resolve().exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")


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
    available_files = []
    for file_path in mcap_dir.glob("*.mcap"):
        try:
            if read_mcap(file_path, 1):
                available_files.append(file_path.name)
        except Exception as e:
            print(f"Cant read file {file_path.name}: {e}")
    return available_files


@app.get("/files/{file_name}")
async def get_mcap_file(request: Request, file_name: str):
    mcap_dir = request.app.state.mcap_dir
    await check_file(mcap_dir, file_name)
    return FileResponse(
        path=(mcap_dir / file_name).resolve(),
        filename=file_name,
        media_type="application/octet-stream"
    )


@app.post("/files")
async def upload_mcap_file(request: Request, file: UploadFile = File(...)) -> dict:
    mcap_dir = request.app.state.mcap_dir
    await check_file(mcap_dir, file.filename, True)
    file_path = mcap_dir / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    if not read_mcap(file_path, 1):
        file_path.unlink()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid or corrupted mcap file")
    return { "filename": file.filename }


@app.delete("/files/{file_name}")
async def del_mcap_file(request: Request, file_name: str) -> None:
    mcap_dir = request.app.state.mcap_dir
    await check_file(mcap_dir, file_name)
    (mcap_dir / file_name).resolve().unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/messages/{file_name}")
async def get_mcap_messages(request: Request, file_name: str, limit: int = Query(default=1000)) -> list[McapMessage]:
    mcap_dir = request.app.state.mcap_dir
    await check_file(mcap_dir, file_name)
    try:
        messages = await asyncio.get_running_loop().run_in_executor(None, read_mcap, (mcap_dir / file_name).resolve(), limit)
        return messages
    except Exception as e:
        print(f"Cant read file {file_name}: {e}")
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
