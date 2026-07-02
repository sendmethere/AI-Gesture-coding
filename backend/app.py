"""FastAPI application: serves the frontend and the analysis API."""
import mimetypes
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    StreamingResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import csv_export, schema_store, settings_store
from .paths import (
    FRONTEND_DIR, VIDEOS_DIR, STRIPS_DIR, RESULTS_DIR, PROMPTS_DIR, ensure_dirs,
)
from .pipeline import JOB

ensure_dirs()

app = FastAPI(title="AI Gesture Coding for Microteaching")

# Holds the path of the currently loaded video (for playback + analysis).
STATE = {"video_path": None}


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #
@app.get("/api/schema")
def get_schema():
    return schema_store.load_schema()


class SchemaBody(BaseModel):
    gestures: list


@app.post("/api/schema")
def post_schema(body: SchemaBody):
    try:
        return schema_store.save_schema(body.dict())
    except ValueError as e:
        raise HTTPException(400, str(e))


# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #
@app.get("/api/settings")
def get_settings():
    return settings_store.public_settings()


class SettingsBody(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    interval: Optional[float] = None
    segment_frames: Optional[int] = None
    start_offset: Optional[float] = None
    max_duration: Optional[float] = None
    min_confidence: Optional[float] = None
    include_confidence: Optional[bool] = None
    save_strips: Optional[bool] = None
    motion_filter: Optional[bool] = None
    still_threshold: Optional[float] = None
    start_threshold: Optional[float] = None
    stt_enabled: Optional[bool] = None
    stt_model: Optional[str] = None
    stt_language: Optional[str] = None


@app.post("/api/settings")
def post_settings(body: SettingsBody):
    patch = {k: v for k, v in body.dict().items() if v is not None}
    settings_store.save_settings(patch)
    return settings_store.public_settings()


# --------------------------------------------------------------------------- #
# Video load / upload / stream
# --------------------------------------------------------------------------- #
class LoadVideoBody(BaseModel):
    path: str


@app.post("/api/load-video")
def load_video(body: LoadVideoBody):
    p = Path(body.path)
    if not p.exists() or not p.is_file():
        raise HTTPException(400, f"file not found: {body.path}")
    STATE["video_path"] = str(p.resolve())
    return {"video_path": STATE["video_path"], "name": p.name}


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    dest = VIDEOS_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    STATE["video_path"] = str(dest.resolve())
    return {"video_path": STATE["video_path"], "name": file.filename}


@app.get("/api/current-video")
def current_video():
    p = STATE["video_path"]
    return {"video_path": p, "name": Path(p).name if p else None}


def _range_stream(path: str, request: Request) -> Response:
    file_size = os.path.getsize(path)
    media = mimetypes.guess_type(path)[0] or "application/octet-stream"
    range_header = request.headers.get("range")
    if range_header is None:
        return FileResponse(path, media_type=media)

    try:
        units, rng = range_header.split("=")
        start_s, end_s = rng.split("-")
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else file_size - 1
    except Exception:
        start, end = 0, file_size - 1
    end = min(end, file_size - 1)
    start = max(0, start)
    length = end - start + 1

    def iter_file(chunk=1024 * 512):
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                data = f.read(min(chunk, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
    }
    return StreamingResponse(
        iter_file(), status_code=206, headers=headers, media_type=media
    )


@app.get("/api/video")
def stream_video(request: Request):
    p = STATE["video_path"]
    if not p or not os.path.exists(p):
        raise HTTPException(404, "no video loaded")
    return _range_stream(p, request)


# --------------------------------------------------------------------------- #
# Analysis control
# --------------------------------------------------------------------------- #
@app.post("/api/analyze")
def start_analysis():
    if not STATE["video_path"] or not os.path.exists(STATE["video_path"]):
        raise HTTPException(400, "no video loaded")
    if JOB.is_running():
        raise HTTPException(409, "analysis already running")
    settings = settings_store.load_settings()
    try:
        JOB.start(STATE["video_path"], settings)
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    return {"status": "running"}


@app.post("/api/stop")
def stop_analysis():
    JOB.request_stop()
    return {"status": "stopping"}


@app.get("/api/status")
def status(since: int = 0):
    return JOB.snapshot(since)


@app.get("/api/strip/{no}")
def get_strip(no: int):
    """Serve the concatenated per-frame preview strip (frames go to the LLM individually)."""
    p = STATE["video_path"]
    if not p:
        raise HTTPException(404, "no video loaded")
    f = STRIPS_DIR / Path(p).stem / f"seg_{no:04d}.png"
    if not f.exists():
        raise HTTPException(
            404, "strip not found (분석 옵션에서 strip 저장이 꺼져 있을 수 있습니다)"
        )
    return FileResponse(f, media_type="image/png")


@app.get("/api/pose/{no}")
def get_pose(no: int):
    """Serve the skeleton-overlay strip (full frames with detected keypoints)."""
    p = STATE["video_path"]
    if not p:
        raise HTTPException(404, "no video loaded")
    f = STRIPS_DIR / Path(p).stem / f"pose_{no:04d}.png"
    if not f.exists():
        raise HTTPException(
            404, "pose overlay not found (모션 필터가 꺼져 있었거나 포즈 추적 실패)"
        )
    return FileResponse(f, media_type="image/png")


@app.get("/api/prompt/{no}")
def get_prompt(no: int):
    """Serve the exact text message that was sent to the AI for this window."""
    p = STATE["video_path"]
    if not p:
        raise HTTPException(404, "no video loaded")
    f = PROMPTS_DIR / Path(p).stem / f"seg_{no:04d}.txt"
    if not f.exists():
        raise HTTPException(404, "prompt not found for this window")
    return FileResponse(f, media_type="text/plain; charset=utf-8")


class UpdateResultBody(BaseModel):
    index: int
    gestures: list


@app.post("/api/result/update")
def update_result(body: UpdateResultBody):
    updated = JOB.update_result(body.index, [str(g) for g in body.gestures])
    if updated is None:
        raise HTTPException(404, "result index out of range")
    return updated


# --------------------------------------------------------------------------- #
# CSV export
# --------------------------------------------------------------------------- #
def _export_filename(ts: Optional[str] = None) -> str:
    """Build `{videotitle}_{YYYYMMDD_HHMMSS}.csv` for the loaded video."""
    p = STATE["video_path"]
    stem = Path(p).stem if p else "gesture"
    stem = re.sub(r"[^\w.\-]+", "_", stem).strip("_") or "gesture"  # filesystem-safe
    ts = ts or datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{stem}_{ts}.csv"


@app.get("/api/export")
def export_csv(confidence: bool = False, download: bool = False, name: str = ""):
    snap = JOB.snapshot(0)
    results = snap["results"]
    if not results:
        raise HTTPException(400, "no results to export")

    # On download, reuse the file already written by the preceding save call
    # (so we don't create a second file with a different timestamp).
    if download and name:
        safe = Path(name).name  # strip any path components
        existing = RESULTS_DIR / safe
        if existing.exists():
            return FileResponse(existing, media_type="text/csv", filename=safe)
        path = csv_export.save_csv(results, include_confidence=confidence, name=safe)
        return FileResponse(path, media_type="text/csv", filename=safe)

    fname = _export_filename()
    path = csv_export.save_csv(results, include_confidence=confidence, name=fname)
    if download:
        return FileResponse(path, media_type="text/csv", filename=fname)
    return {"path": path, "rows": len(results), "name": fname}


class HumanExportBody(BaseModel):
    coder: Optional[str] = ""
    rows: list


@app.post("/api/human-export")
def human_export(body: HumanExportBody):
    """Save a human coder's per-window codes to results/{video}_human_{coder}_{ts}.csv."""
    if not body.rows:
        raise HTTPException(400, "no human codings to export")
    coder_raw = (body.coder or "").strip()
    coder_safe = re.sub(r"[^\w.\-]+", "_", coder_raw).strip("_") or "coder"
    p = STATE["video_path"]
    stem = Path(p).stem if p else "gesture"
    stem = re.sub(r"[^\w.\-]+", "_", stem).strip("_") or "gesture"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{stem}_human_{coder_safe}_{ts}.csv"
    path = csv_export.save_human_csv(body.rows, coder_raw or coder_safe, fname)
    return {"path": path, "rows": len(body.rows), "name": fname}


# --------------------------------------------------------------------------- #
# Frontend (mounted last so /api/* wins)
# --------------------------------------------------------------------------- #
@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
