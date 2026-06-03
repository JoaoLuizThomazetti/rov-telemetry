import os
import cv2
import shutil
import logging
import asyncio
from pathlib import Path
from av import VideoFrame
from pydantic import BaseModel, Field
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from aiortc.mediastreams import VideoStreamTrack
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Response, HTTPException, status, Request, UploadFile, File
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer


logger = logging.getLogger("uvicorn.error")

config = RTCConfiguration(iceServers=[
    RTCIceServer(urls="stun:stun.l.google.com:19302")
])

VIDEO_DIR = Path(os.environ.get("VIDEO_DIR", "/videos"))


class OfferRequest(BaseModel):
    sdp: str = Field(description="SDP offer")
    type: str = Field(description="SDP type")
    source_type: str = Field(description="Video source type")
    source_id: str | int = Field(description="File path or camera index")


class OfferResponse(BaseModel):
    sdp: str = Field(description="SDP offer")
    type: str = Field(description="SDP type")


class UploadResponse(BaseModel):
    filename: str = Field(description="Uploaded file name")


class VideoSources(BaseModel):
    videos: list[str] = Field(description="Available video files")
    cameras: list[int] = Field(description="Available cameras")


class CvTrack(VideoStreamTrack):
    def __init__(self, source: str | int, loop: bool = False):
        super().__init__()
        self.cap = cv2.VideoCapture(source)
        self.loop = loop

    async def recv(self) -> VideoFrame:
        loop = asyncio.get_running_loop()
        ret, frame = await loop.run_in_executor(None, self.cap.read)
        if not ret:
            if self.loop:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = await loop.run_in_executor(None, self.cap.read)
            if not ret:
                raise Exception("Failed to read frame")
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        pts, time_base = await self.next_timestamp()
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

    def stop(self):
        self.cap.release()
        super().stop()


def test_video(file_path: Path) -> bool:
    cap = cv2.VideoCapture(str(file_path))
    if not cap.isOpened():
        return False
    ret, _ = cap.read()
    cap.release()
    return ret


def check_file(video_dir: Path, file_name: str, is_upload: bool = False) -> None:
    if not file_name.endswith(".mp4"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be .mp4")
    if not (video_dir / file_name).resolve().is_relative_to(video_dir.resolve()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")
    if is_upload:
        if (video_dir / file_name).resolve().exists():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="File already exists")
    else:
        if not (video_dir / file_name).resolve().exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    samples_dir = Path(__file__).parent / "samples"
    for sample in samples_dir.glob("*.mp4"):
        dest = VIDEO_DIR / sample.name
        if not dest.exists():
            shutil.copy(sample, dest)
    peer_conns: set[RTCPeerConnection] = set()
    app.state.peer_conns = peer_conns
    app.state.video_dir = VIDEO_DIR
    yield
    for peer_conn in app.state.peer_conns:
        await peer_conn.close()


app = FastAPI(
    title="Vision API",
    description="Video streaming over WebRTC",
    lifespan=lifespan,
    version="1.0.0",
    root_path="/vision",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health", tags=["HEALTH"])
async def get_health():
    """Health check"""
    return {"status": "ok"}


@app.get("/sources", tags=["SOURCE"], responses={
    500: {"description": "Internal server error"}
})
async def get_sources(request: Request) -> VideoSources:
    """List all available video sources"""
    video_dir = request.app.state.video_dir
    sources = VideoSources(
        videos=[],
        cameras=[],
    )
    try:
        sources.videos = [f.name for f in Path(video_dir).glob('*.mp4')]
        for i in range(4):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cap.release()
                sources.cameras.append(i)
    except Exception as e:
        logger.warning(f"Error: {e}")
    return sources


@app.post("/videos", tags=["VIDEO"], responses={
    400: {"description": "Invalid file extension"},
    409: {"description": "File already exists"},
    422: {"description": "Invalid or corrupted video file"},
})
async def upload_video(request: Request, file: UploadFile = File(...)) -> UploadResponse:
    """Upload a new video file. Rejects corrupted or wrong extension file"""
    video_dir = request.app.state.video_dir
    check_file(video_dir, file.filename, True)
    file_path = video_dir / file.filename
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)
    if not test_video(file_path):
        file_path.unlink()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid or corrupted video file")
    return UploadResponse(filename=file.filename)


@app.delete("/videos/{file_name}", tags=["VIDEO"], responses={
    400: {"description": "Invalid file extension or path"},
    404: {"description": "File not found"},
    204: {"description": "Video deleted successfully"},
})
async def delete_video(request: Request, file_name: str) -> None:
    """Delete video file by name"""
    video_dir = request.app.state.video_dir
    check_file(video_dir, file_name)
    (video_dir / file_name).resolve().unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/offer", tags=["RTC"], responses={500: {"description": "Internal server error"}})
async def post_offer(request: Request, offer: OfferRequest) -> OfferResponse:
    """WebRTC signaling"""
    video_dir = request.app.state.video_dir
    peer_conns = app.state.peer_conns
    for old in set(peer_conns):
        await old.close()
    peer_conns.clear()
    peer_conn = RTCPeerConnection(configuration=config)
    source = str(video_dir / offer.source_id) if offer.source_type == "video" else int(offer.source_id)
    track = CvTrack(source, loop=offer.source_type == "video")
    peer_conn.addTrack(track)
    await peer_conn.setRemoteDescription(RTCSessionDescription(sdp=offer.sdp, type=offer.type))
    answer = await peer_conn.createAnswer()
    await peer_conn.setLocalDescription(answer)
    while peer_conn.iceGatheringState != "complete":
        await asyncio.sleep(0.1)

    @peer_conn.on("connectionstatechange")
    async def on_state():
        if peer_conn.connectionState in ("failed", "closed"):
            await peer_conn.close()
            peer_conns.discard(peer_conn)

    peer_conns.add(peer_conn)
    return OfferResponse(
        sdp=peer_conn.localDescription.sdp,
        type=peer_conn.localDescription.type
    )
