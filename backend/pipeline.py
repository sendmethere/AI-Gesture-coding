"""Analysis pipeline + background job manager (plan.md Steps 1-6).

Flow per segment:
  extract N frames at `interval`  ->  crop teacher (YOLO/fallback)
  -> resize + annotate each frame  ->  LLM Vision (frames sent individually)
  -> result row
The annotated frames are also concatenated into one strip image, but only as a
saved/previewable record — the LLM receives them as separate images (UPDATE.md).
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
from PIL import Image, ImageDraw

from . import llm
from .detector import get_detector
from .motion import get_analyzer
from .stt import get_transcriber, speech_in_window
from .paths import STRIPS_DIR, LOGS_DIR, PROMPTS_DIR
from .schema_store import load_schema

STRIP_HEIGHT = 240  # px; frames are resized to this height before concat
BAR_H = 18          # px; motion colorbar height drawn at the bottom of each frame

# Motion state -> colorbar RGB (plan.v2 §4.2). The gesture start frame is forced
# to green; sustained motion after it shows blue.
STATE_COLOR = {
    "still": (120, 120, 120),  # gray  — no motion
    "prep": (235, 200, 40),    # yellow — preparation
    "move": (40, 130, 220),    # blue  — gesture in progress
    "start": (40, 200, 90),    # green — gesture start ★
}


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
        self.phase = "idle"   # idle | transcribing | analyzing
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
                "phase": self.phase,
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
            self.phase = "analyzing"
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
        interval = float(settings.get("interval", 0.3)) or 0.3
        seg_frames = int(settings.get("segment_frames", 10)) or 10
        provider = settings.get("provider", "mock")
        api_key = settings.get("api_key", "")
        model = settings.get("model", "")
        save_strips = bool(settings.get("save_strips", True))
        start_offset = float(settings.get("start_offset", 0) or 0)  # seconds
        max_duration = float(settings.get("max_duration", 0) or 0)  # 0 = no limit
        min_conf = float(settings.get("min_confidence", 0) or 0)    # 0 = off
        motion_filter = bool(settings.get("motion_filter", True))
        still_thr = float(settings.get("still_threshold", 0.05) or 0.05)
        start_thr = float(settings.get("start_threshold", 0.3) or 0.3)
        stt_enabled = bool(settings.get("stt_enabled", False))
        stt_model = settings.get("stt_model", "base") or "base"
        stt_language = settings.get("stt_language", "") or ""
        schema = load_schema()

        detector = get_detector()
        analyzer = get_analyzer() if motion_filter else None
        self.detector_status = detector.status()
        if analyzer is not None:
            self.detector_status += f" · motion:{analyzer.status()}"
        self.log(f"[start] {Path(video_path).name} detector={self.detector_status}")
        if motion_filter:
            self.log(
                f"[motion] filter on (start threshold {start_thr:g}) — segments "
                "with no frame reaching it are auto-coded GT-None (token save)"
            )

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

        # ----- speech transcription for the analyzed range (plan.v2 §1.2) --- #
        transcript: List[dict] = []
        if stt_enabled and total_segments > 0:
            stt_end = start_offset + total_segments * seg_len
            transcriber = get_transcriber(stt_model, stt_language)
            if transcriber.available:
                self.detector_status += f" · stt:{transcriber.status()}"
                self.phase = "transcribing"
                self.log(
                    f"[stt] transcribing {format_ts(start_offset)}~"
                    f"{format_ts(stt_end)} with {transcriber.status()} …"
                )

                def _stt_progress(sec: float) -> None:
                    self.current_seconds = sec  # drives the live "up to" readout
                    self.log(f"  ↳ transcribed up to {format_ts(sec)}")

                try:
                    transcript = transcriber.transcribe_range(
                        video_path, start_offset, stt_end, progress=_stt_progress
                    )
                    self.log(f"[stt] done — {len(transcript)} utterances")
                except Exception as e:
                    self.log(f"[stt-error] {e}")
                    transcript = []
                finally:
                    self.phase = "analyzing"
            else:
                self.log(
                    "[stt] enabled but faster-whisper is unavailable "
                    "(pip install -r requirements-stt.txt) — skipping"
                )

        strip_dir = STRIPS_DIR / Path(video_path).stem
        if save_strips:
            strip_dir.mkdir(parents=True, exist_ok=True)
        # Per-window prompt text is always saved (tiny) so the exact message sent
        # to the AI can be reviewed later.
        prompt_dir = PROMPTS_DIR / Path(video_path).stem
        prompt_dir.mkdir(parents=True, exist_ok=True)

        seg_index = 0
        while seg_index < total_segments:
            if self._stop.is_set():
                self.log("[stop] requested by user")
                break

            seg_start = start_offset + seg_index * seg_len
            self.current_seconds = seg_start
            frames = []  # full frames (pose runs on these for a stable reference)
            crops = []   # teacher crops (used to build the strip image)
            for f in range(seg_frames):
                t = seg_start + f * interval
                cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
                frames.append(frame)
                crops.append(detector.crop_teacher(frame))

            if not crops:
                # reached end of stream
                with self.lock:
                    self.total = seg_index  # correct the total
                break

            # ----- motion pre-analysis + grading (plan.v2 §3, §5.1) -------- #
            motion = (
                analyzer.analyze(frames, still_thr, start_thr)
                if analyzer is not None
                else None
            )
            grade, source = self._grade(motion, start_thr)

            # Speech spoken during this window (plan.v2 §1.2).
            speech = speech_in_window(transcript, seg_start, seg_start + seg_len)

            timestamps = [
                format_ts(seg_start + f * interval) for f in range(len(crops))
            ]
            # Per-frame annotated images: sent to the LLM individually (each
            # encoded at full resolution) and concatenated only for the record.
            frame_imgs = self._frame_images(
                crops,
                states=(motion or {}).get("states"),
                per_frame=(motion or {}).get("per_frame"),
                start_frame=(motion or {}).get("start_frame", 0),
                timestamps=timestamps,
            )
            frame_pngs = [self._png_bytes(im) for im in frame_imgs]
            if save_strips:
                try:
                    strip = self._concat_strip(frame_imgs)
                    strip.save(strip_dir / f"seg_{seg_index + 1:04d}.png")
                except Exception:
                    pass
                # Scientific record: full-frame strip with the detected skeleton
                # overlaid (pose verification). Only when pose actually tracked.
                if motion and motion.get("points"):
                    try:
                        pose = self._make_pose_strip(frames, motion, timestamps)
                        if pose is not None:
                            pose.save(strip_dir / f"pose_{seg_index + 1:04d}.png")
                    except Exception:
                        pass

            motion_desc = (motion or {}).get("description", "")
            if grade == "C":
                # Near-still + skeleton OK → GT-None automatically, no AI tokens.
                gestures, confidence = [], 1.0
                self.log(
                    f"  ↳ grade C: motion {motion['max_change']:g} < {start_thr:g}"
                    " → GT-None (AI skipped)"
                )
                prompt_text = (
                    "[grade C — AI call skipped by the motion pre-filter]\n"
                    f"No frame reached the start threshold ({start_thr:g}); "
                    "auto-coded GT-N (no gesture). No message was sent to the AI.\n\n"
                    f"motion: {motion_desc}"
                )
            else:
                prompt_text = llm.build_prompt(schema, speech, motion_desc)
                try:
                    res = llm.analyze_frames(
                        provider, api_key, model, frame_pngs, schema, seg_index,
                        speech=speech, motion_desc=motion_desc,
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

            # Save the exact message (text) sent to the AI for later review.
            try:
                (prompt_dir / f"seg_{seg_index + 1:04d}.txt").write_text(
                    prompt_text, encoding="utf-8"
                )
            except Exception:
                pass

            review_flag = self._review_flag(grade, confidence)
            row = {
                "no": seg_index + 1,
                "seconds": seg_start,
                "timestamp": format_ts(seg_start),
                "gesture": gestures,
                "confidence": confidence,
                "edited": False,
                "grade": grade,
                "motion": (motion or {}).get("max_change"),
                "source": source,
                "review_flag": review_flag,
                "speech": speech,
            }
            with self.lock:
                self.results.append(row)
                self.done = seg_index + 1
            grade_tag = f"[{grade}] " if grade else ""
            flag_tag = " ⚑" if review_flag else ""
            self.log(
                f"{format_ts(seg_start)}~{format_ts(seg_start + seg_len)}  "
                f"{grade_tag}{row['gesture']}  ({row['confidence']}){flag_tag}"
            )
            seg_index += 1

        cap.release()

    # ----- grading (plan.v2 §5.1, §7) ----------------------------------- #
    @staticmethod
    def _grade(motion: Optional[dict], start_thr: float) -> tuple:
        """Return (grade, detection_source).

        A = skeleton OK + a frame reaches the gesture-start threshold → AI codes
        B = skeleton detection failed                → AI judges (review needed)
        C = skeleton OK but NO frame reaches start_thr (no codeable gesture)
            → GT-None auto, AI skipped (plan §3.2 / §5.1, the token-saving path)
        "" = motion filter disabled                  → AI codes (legacy behavior)

        Gating on the START threshold (not the still threshold) is deliberate:
        with real pose tracking there is always a small jitter floor, so a
        single low-motion frame is never "perfectly still". A segment is only
        worth AI tokens if motion actually rises to gesture level somewhere in
        the window.
        """
        if motion is None:
            return "", None
        source = motion.get("source")
        if not motion.get("ok"):
            return "B", "skeleton_fail"
        if motion.get("max_change", 0.0) < start_thr:
            return "C", source
        return "A", source

    @staticmethod
    def _review_flag(grade: str, confidence: float) -> bool:
        """plan.v2 §7.2 — flag segments a researcher should double-check."""
        if grade == "B":
            return True          # skeleton detection failed
        if grade == "C":
            return False         # auto GT-None, high certainty
        if confidence and confidence < 0.75:
            return True
        return False

    # ----- imaging helpers ---------------------------------------------- #
    def _frame_images(
        self,
        crops: List[np.ndarray],
        states: Optional[List[str]] = None,
        per_frame: Optional[List[float]] = None,
        start_frame: int = 0,
        timestamps: Optional[List[str]] = None,
    ) -> List[Image.Image]:
        """One annotated PIL image per frame.

        Each crop is resized to STRIP_HEIGHT and, when motion data is present,
        gets its own motion colorbar + timestamp/change label. These are the
        images sent to the LLM individually (each encoded at full resolution),
        and the same list is concatenated by `_make_strip` for the saved record.
        """
        annotate = bool(states)  # only when motion data is available
        bar_h = BAR_H if annotate else 0
        out: List[Image.Image] = []
        for i, c in enumerate(crops):
            rgb = cv2.cvtColor(c, cv2.COLOR_BGR2RGB)
            im = Image.fromarray(rgb)
            w = max(1, int(im.width * (STRIP_HEIGHT / im.height)))
            im = im.resize((w, STRIP_HEIGHT))
            if not annotate:
                out.append(im)
                continue

            canvas = Image.new("RGB", (im.width, STRIP_HEIGHT + bar_h), (0, 0, 0))
            canvas.paste(im, (0, 0))
            draw = ImageDraw.Draw(canvas)
            st = states[i] if i < len(states) else "still"
            if start_frame and i + 1 == start_frame:
                st = "start"
            color = STATE_COLOR.get(st, STATE_COLOR["still"])
            draw.rectangle(
                [0, STRIP_HEIGHT, im.width - 1, STRIP_HEIGHT + bar_h - 1], fill=color
            )
            label = []
            if timestamps and i < len(timestamps):
                label.append(timestamps[i])
            if per_frame and i < len(per_frame):
                label.append(f"{per_frame[i]:.2f}")
            if label:
                txt = " ".join(label)
                tx, ty = 3, STRIP_HEIGHT + 4
                # outline for legibility over any bar color
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    draw.text((tx + dx, ty + dy), txt, fill=(0, 0, 0))
                draw.text((tx, ty), txt, fill=(255, 255, 255))
            out.append(canvas)
        return out

    @staticmethod
    def _concat_strip(imgs: List[Image.Image]) -> Image.Image:
        """Concatenate per-frame images horizontally (saved record only)."""
        total_w = sum(im.width for im in imgs)
        h = max((im.height for im in imgs), default=STRIP_HEIGHT)
        strip = Image.new("RGB", (total_w, h), (0, 0, 0))
        x = 0
        for im in imgs:
            strip.paste(im, (x, 0))
            x += im.width
        return strip

    def _make_strip(self, *args, **kwargs) -> Image.Image:
        """Annotated per-frame images concatenated into one strip image."""
        return self._concat_strip(self._frame_images(*args, **kwargs))

    @staticmethod
    def _draw_skeleton(frame: np.ndarray, pt: dict) -> None:
        """Overlay the tracked keypoints on a FULL frame (in place, BGR).

        Shows exactly what YOLO-pose detected and the two quantities the motion
        metric is built from: the shoulder line (the normalizer) and the wrist
        markers (whose displacement is measured). A scientific record of how the
        pose was recognized and the change measured.
        """
        ls, rs = pt.get("ls"), pt.get("rs")
        lw, rw = pt.get("lw"), pt.get("rw")

        def ip(p):
            return (int(round(p[0])), int(round(p[1])))

        # shoulder line = the normalizer (cyan)
        if ls and rs:
            cv2.line(frame, ip(ls), ip(rs), (255, 200, 0), 3)
        # shoulder→wrist links (green) + wrist markers (red = what's measured)
        for s, w in ((ls, lw), (rs, rw)):
            if s and w:
                cv2.line(frame, ip(s), ip(w), (80, 220, 80), 2)
        for p in (ls, rs):
            if p:
                cv2.circle(frame, ip(p), 5, (255, 200, 0), -1)
        for p in (lw, rw):
            if p:
                cv2.circle(frame, ip(p), 7, (0, 0, 255), -1)

    def _make_pose_strip(
        self,
        frames: List[np.ndarray],
        motion: dict,
        timestamps: Optional[List[str]] = None,
    ) -> Optional[Image.Image]:
        """Skeleton-overlay strip from the FULL frames pose actually ran on.

        Returns None when there are no per-frame keypoints (framediff fallback or
        pose failure) — nothing to verify in that case.
        """
        points = motion.get("points")
        if not points:
            return None
        drawn = []
        for i, f in enumerate(frames):
            c = f.copy()
            if i < len(points) and points[i]:
                self._draw_skeleton(c, points[i])
            drawn.append(c)
        return self._make_strip(
            drawn,
            states=motion.get("states"),
            per_frame=motion.get("per_frame"),
            start_frame=motion.get("start_frame", 0),
            timestamps=timestamps,
        )

    def _png_bytes(self, img: Image.Image) -> bytes:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


# Singleton job used by the API.
JOB = AnalysisJob()
