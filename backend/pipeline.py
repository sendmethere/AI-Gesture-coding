"""Analysis pipeline + background job manager (plan.md Steps 1-6).

Flow per segment:
  extract N frames at `interval`  ->  crop teacher (YOLO/fallback)
  -> resize + concat horizontally into a strip  ->  LLM Vision  -> result row
Results stream into an in-memory job that the API polls for live updates.
"""
import io
import threading
import time
import traceback
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from PIL import Image

from . import llm
from .detector import get_detector
from .paths import STRIPS_DIR, LOGS_DIR
from .schema_store import load_schema

STRIP_HEIGHT = 240  # px; frames are resized to this height before concat


def format_ts(seconds: float) -> str:
    seconds = int(round(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class AnalysisJob:
    def __init__(self):
        self.lock = threading.Lock()
        self.results: List[dict] = []
        self.logs: List[str] = []
        self.total = 0
        self.done = 0
        self.current_seconds = 0.0  # start time of the segment being processed
        self.status = "idle"  # idle | running | done | stopped | error
        self.error: Optional[str] = None
        self.video_path: Optional[str] = None
        self.detector_status = ""
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ----- live snapshot for the API ------------------------------------- #
    def snapshot(self, since: int = 0) -> dict:
        with self.lock:
            return {
                "status": self.status,
                "total": self.total,
                "done": self.done,
                "current_seconds": self.current_seconds,
                "error": self.error,
                "detector": self.detector_status,
                "results": self.results[since:],
                "result_count": len(self.results),
                "logs": self.logs[-50:],
            }

    def log(self, msg: str) -> None:
        with self.lock:
            self.logs.append(msg)
        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            with open(LOGS_DIR / "analysis.log", "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

    def is_running(self) -> bool:
        return self.status == "running"

    def request_stop(self) -> None:
        self._stop.set()

    def update_result(self, index: int, gestures: List[str]) -> Optional[dict]:
        with self.lock:
            if 0 <= index < len(self.results):
                self.results[index]["gesture"] = list(gestures)
                self.results[index]["edited"] = True
                return dict(self.results[index])
        return None

    # ----- run ----------------------------------------------------------- #
    def start(self, video_path: str, settings: dict) -> None:
        if self.is_running():
            raise RuntimeError("analysis already running")
        with self.lock:
            self.results = []
            self.logs = []
            self.total = 0
            self.done = 0
            self.current_seconds = 0.0
            self.status = "running"
            self.error = None
            self.video_path = video_path
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, args=(video_path, settings), daemon=True
        )
        self._thread.start()

    def _run(self, video_path: str, settings: dict) -> None:
        try:
            self._analyze(video_path, settings)
            with self.lock:
                if self._stop.is_set():
                    self.status = "stopped"
                else:
                    self.status = "done"
            self.log(f"[done] status={self.status} segments={self.done}")
        except Exception as e:
            with self.lock:
                self.status = "error"
                self.error = str(e)
            self.log("[error] " + str(e))
            self.log(traceback.format_exc())

    def _analyze(self, video_path: str, settings: dict) -> None:
        interval = float(settings.get("interval", 0.5)) or 0.5
        seg_frames = int(settings.get("segment_frames", 6)) or 6
        provider = settings.get("provider", "mock")
        api_key = settings.get("api_key", "")
        model = settings.get("model", "")
        save_strips = bool(settings.get("save_strips", True))
        start_offset = float(settings.get("start_offset", 0) or 0)  # seconds
        max_duration = float(settings.get("max_duration", 0) or 0)  # 0 = no limit
        min_conf = float(settings.get("min_confidence", 0) or 0)    # 0 = off
        schema = load_schema()

        detector = get_detector()
        self.detector_status = detector.status()
        self.log(f"[start] {Path(video_path).name} detector={self.detector_status}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"cannot open video: {video_path}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        duration = (frame_count / fps) if fps > 0 else 0
        seg_len = interval * seg_frames  # seconds per segment

        if duration <= 0:
            # Fallback: probe by reading; assume unknown length, stop on EOF.
            self.log("[warn] unknown duration; will read until end of stream")
            total_segments = (
                max(1, int(max_duration // seg_len)) if max_duration > 0 else 10_000
            )
        else:
            end = duration
            if max_duration > 0:
                end = min(duration, start_offset + max_duration)
            available = end - start_offset
            total_segments = max(0, int(available // seg_len))
        if start_offset > 0:
            self.log(f"[start] from {format_ts(start_offset)}")
        if max_duration > 0:
            self.log(f"[limit] {max_duration:g}s window")
        if total_segments == 0:
            self.log("[warn] no segments in the selected range")
        with self.lock:
            self.total = total_segments

        strip_dir = STRIPS_DIR / Path(video_path).stem
        if save_strips:
            strip_dir.mkdir(parents=True, exist_ok=True)

        seg_index = 0
        while seg_index < total_segments:
            if self._stop.is_set():
                self.log("[stop] requested by user")
                break

            seg_start = start_offset + seg_index * seg_len
            self.current_seconds = seg_start
            crops = []
            for f in range(seg_frames):
                t = seg_start + f * interval
                cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
                crop = detector.crop_teacher(frame)
                crops.append(crop)

            if not crops:
                # reached end of stream
                with self.lock:
                    self.total = seg_index  # correct the total
                break

            strip = self._make_strip(crops)
            strip_png = self._png_bytes(strip)
            if save_strips:
                try:
                    strip.save(strip_dir / f"seg_{seg_index + 1:04d}.png")
                except Exception:
                    pass

            try:
                res = llm.analyze_strip(
                    provider, api_key, model, strip_png, schema, seg_index
                )
            except Exception as e:
                res = {"gestures": [], "confidence": 0.0, "error": str(e)}
                self.log(f"[llm-error] seg {seg_index + 1}: {e}")

            gestures = res.get("gestures", [])
            confidence = res.get("confidence", 0.0)
            # Force low-confidence segments to None.
            if min_conf > 0 and confidence < min_conf and gestures:
                self.log(
                    f"  ↳ conf {confidence} < {min_conf} → None "
                    f"(dropped {gestures})"
                )
                gestures = []

            row = {
                "no": seg_index + 1,
                "seconds": seg_start,
                "timestamp": format_ts(seg_start),
                "gesture": gestures,
                "confidence": confidence,
                "edited": False,
            }
            with self.lock:
                self.results.append(row)
                self.done = seg_index + 1
            self.log(
                f"{format_ts(seg_start)}~{format_ts(seg_start + seg_len)}  "
                f"{row['gesture']}  ({row['confidence']})"
            )
            seg_index += 1

        cap.release()

    # ----- imaging helpers ---------------------------------------------- #
    def _make_strip(self, crops: List[np.ndarray]) -> Image.Image:
        imgs = []
        for c in crops:
            rgb = cv2.cvtColor(c, cv2.COLOR_BGR2RGB)
            im = Image.fromarray(rgb)
            w = max(1, int(im.width * (STRIP_HEIGHT / im.height)))
            imgs.append(im.resize((w, STRIP_HEIGHT)))
        total_w = sum(im.width for im in imgs)
        strip = Image.new("RGB", (total_w, STRIP_HEIGHT), (0, 0, 0))
        x = 0
        for im in imgs:
            strip.paste(im, (x, 0))
            x += im.width
        return strip

    def _png_bytes(self, img: Image.Image) -> bytes:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


# Singleton job used by the API.
JOB = AnalysisJob()
