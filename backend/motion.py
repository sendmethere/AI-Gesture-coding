"""Skeleton / motion pre-analysis (plan.v2 §2-3).

Goal: cheaply estimate how much the teacher actually MOVES in a segment so the
pipeline can skip near-still segments (auto GT-None) and only spend AI tokens on
segments that contain real motion. This is the core token-saving mechanism in
plan2 §9.

Two backends, chosen automatically (same graceful-fallback pattern as
detector.py):

  * "skeleton"  — Ultralytics YOLO-pose. Tracks shoulders + wrists, computes
                  per-frame wrist displacement normalized by shoulder width
                  (plan §2.2, §3.1). Distance/body-size invariant and localized
                  to the hands, so still segments score near 0.
  * "framediff" — pure OpenCV fallback when ultralytics/weights are unavailable.
                  Mean absolute pixel difference between consecutive frames. This
                  is COARSE (it also picks up background/camera motion) and is
                  only a last resort; stillness gating and start detection are
                  far less reliable on it.

Pose runs on the FULL frame (not the teacher crop): the crop box shifts frame to
frame, which would inject spurious displacement, whereas full-frame pixel
coordinates give a stable reference.

Both backends return the same summary shape so the pipeline doesn't care which
ran.
"""
from typing import List, Optional

import cv2
import numpy as np

# COCO-17 keypoint indices used by YOLO-pose.
L_SHOULDER, R_SHOULDER = 5, 6
L_WRIST, R_WRIST = 9, 10
KP_CONF_MIN = 0.30  # keypoint confidence threshold

# framediff motion is on a different scale than the normalized skeleton metric;
# this gain maps it into roughly the same range so similar thresholds apply.
FRAMEDIFF_GAIN = 6.0
FRAMEDIFF_SIZE = (160, 160)  # downscale before diffing (speed + denoise)


def _state(change: float, still_thr: float, start_thr: float) -> str:
    """Map a per-frame change value to a coarse motion state (plan §3.2)."""
    if change < still_thr:
        return "still"
    if change < start_thr:
        return "prep"
    return "move"


class MotionAnalyzer:
    def __init__(self, model_name: str = "yolov8n-pose.pt"):
        self.backend = "framediff"
        self.model = None
        try:
            from ultralytics import YOLO  # type: ignore

            self.model = YOLO(model_name)
            self.backend = "skeleton"
        except Exception:
            self.model = None  # ultralytics/weights unavailable → framediff

    def status(self) -> str:
        return "yolo-pose" if self.backend == "skeleton" else "frame-diff"

    # ----- public API ---------------------------------------------------- #
    def analyze(
        self,
        frames: List[np.ndarray],
        still_thr: float = 0.05,
        start_thr: float = 0.15,
    ) -> dict:
        """Summarize motion across one segment's (FULL) frames.

        Returns:
          source       "skeleton" | "framediff"
          ok           True if the chosen backend produced a usable signal
                       (skeleton: landmarks tracked; framediff: always True)
          per_frame    change value per frame (frame 0 = 0.0)
          states       per-frame state: "still" | "prep" | "move"
          max_change   peak per-frame change
          start_frame  1-based index of the detected gesture onset, or 0
        """
        if not frames:
            return self._empty("framediff")

        if self.backend == "skeleton":
            res = self._skeleton(frames)
            if res is not None:
                return self._summarize(
                    "skeleton", res["per_frame"], True, still_thr, start_thr,
                    vecs=res["vecs"], points=res["points"],
                    base_sw=res["base_sw"],
                )
            # Pose failed for this segment (occlusion, side view, blur, …):
            # plan §2.3 → treat as detection failure but still give a framediff
            # signal so the colorbar/threshold logic has something to show.
            fd = self._framediff(frames)
            return self._summarize("framediff", fd, False, still_thr, start_thr)

        fd = self._framediff(frames)
        return self._summarize("framediff", fd, True, still_thr, start_thr)

    # ----- backends ------------------------------------------------------ #
    def _skeleton(self, frames: List[np.ndarray]) -> Optional[dict]:
        """Per-frame max(both-wrist) displacement, normalized by shoulder width.

        Returns {"per_frame": [...], "vecs": [...], "points": [...],
        "base_sw": float} where vecs[i] is the dominant wrist's normalized motion
        vector for that frame ({dx, dy, side}) used to describe direction in
        words, and points[i] holds the raw pixel keypoints ({ls, rs, lw, rw},
        each (x, y) or None) so the overlay can show exactly what was detected.
        Returns None when too many frames lack the landmarks needed to measure
        motion reliably (plan §2.3).
        """
        results = self.model(frames, verbose=False)

        wrists: List[Optional[tuple]] = []  # ((lx,ly),(rx,ry)) per frame, px
        shoulder_w: List[Optional[float]] = []
        points: List[dict] = []  # raw px keypoints per frame, for the overlay
        for r in results:
            kp = getattr(r, "keypoints", None)
            boxes = getattr(r, "boxes", None)
            if kp is None or kp.xy is None or len(kp.xy) == 0:
                wrists.append(None)
                shoulder_w.append(None)
                points.append({"ls": None, "rs": None, "lw": None, "rw": None})
                continue
            # Pick the largest detected person (matches detector.py cropping).
            idx = 0
            if boxes is not None and len(boxes) > 1:
                areas = []
                for b in boxes.xywh.tolist():
                    areas.append(b[2] * b[3])
                idx = int(np.argmax(areas))
            xy = kp.xy[idx].cpu().numpy()
            conf = (
                kp.conf[idx].cpu().numpy()
                if getattr(kp, "conf", None) is not None
                else np.ones(len(xy))
            )

            def pt(i):
                return (float(xy[i][0]), float(xy[i][1])) if conf[i] >= KP_CONF_MIN else None

            ls, rs = pt(L_SHOULDER), pt(R_SHOULDER)
            if ls and rs:
                sw = float(np.hypot(ls[0] - rs[0], ls[1] - rs[1]))
            else:
                sw = None
            shoulder_w.append(sw)

            lw, rw = pt(L_WRIST), pt(R_WRIST)
            wrists.append((lw, rw) if (lw or rw) else None)
            points.append({"ls": ls, "rs": rs, "lw": lw, "rw": rw})

        valid_sw = [s for s in shoulder_w if s and s > 1e-3]
        usable = sum(1 for w in wrists if w is not None)
        # Fail the segment if shoulders or wrists are missing in most frames.
        if not valid_sw or usable < max(2, len(frames) // 2):
            return None

        base_sw = float(np.median(valid_sw))  # fixed segment baseline (plan §2.2)
        frame_w = frames[0].shape[1] if frames else 1

        per_frame = [0.0]
        vecs: List[Optional[dict]] = [None]
        for i in range(1, len(frames)):
            prev, cur = wrists[i - 1], wrists[i]
            if prev is None or cur is None:
                per_frame.append(0.0)
                vecs.append(None)
                continue
            change = 0.0
            best = None
            for a, b in zip(prev, cur):  # left wrist, right wrist
                if a is None or b is None:
                    continue
                ndx = (b[0] - a[0]) / base_sw
                ndy = (b[1] - a[1]) / base_sw
                d = float(np.hypot(ndx, ndy))
                if d > change:
                    change = d
                    # describe by IMAGE side (matches what the model sees), not
                    # anatomical left/right which is mirrored in the frame.
                    side = "left" if b[0] < frame_w / 2 else "right"
                    best = {"dx": ndx, "dy": ndy, "side": side}
            per_frame.append(change)
            vecs.append(best)
        return {
            "per_frame": per_frame,
            "vecs": vecs,
            "points": points,
            "base_sw": base_sw,
        }

    def _framediff(self, frames: List[np.ndarray]) -> List[float]:
        grays = []
        for c in frames:
            g = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)
            grays.append(cv2.resize(g, FRAMEDIFF_SIZE).astype(np.float32) / 255.0)
        per_frame = [0.0]
        for i in range(1, len(grays)):
            diff = float(np.mean(np.abs(grays[i] - grays[i - 1])))
            per_frame.append(min(1.0, diff * FRAMEDIFF_GAIN))
        return per_frame

    # ----- shared --------------------------------------------------------- #
    @staticmethod
    def _smooth(per_frame: List[float]) -> List[float]:
        """Median-of-3 filter to kill single-frame keypoint-jitter spikes
        (plan §2.3 "coordinate jump"). An isolated large value between two small
        ones is almost always a pose misdetection, not a real gesture; real
        motion spans several frames and survives the median. Frame 0 stays 0.0.
        """
        n = len(per_frame)
        if n < 3:
            return list(per_frame)
        out = [per_frame[0]]
        for i in range(1, n - 1):
            out.append(float(np.median(per_frame[i - 1 : i + 2])))
        out.append(per_frame[-1])
        return out

    @staticmethod
    def _detect_start(per_frame: List[float], still_thr: float, start_thr: float) -> int:
        """Gesture onset via acceleration (plan §3.3).

        The start is the frame where motion ramps UP into the gesture: the
        previous frame is below the start threshold and this frame crosses it
        with a positive jump. Among qualifying onsets, the sharpest acceleration
        wins. Returns a 1-based index, or 0 if no onset is *captured in this
        window* — i.e. the segment is still, OR the hand was already moving when
        the window opened (a true onset there belongs to an earlier window; the
        sliding window in plan §4.1 is meant to catch it cleanly).

        We start scanning at i=2 on purpose: per_frame[0] is forced to 0.0 (it is
        a window boundary, not a real measurement), so frame 1 must NOT be
        treated as a still→move transition. Requiring a real measured "before"
        frame kills the spurious "every gesture starts at frame 2" artifact.
        """
        best_i = 0
        best_accel = 0.0
        for i in range(2, len(per_frame)):
            if per_frame[i] < start_thr:
                continue
            if per_frame[i - 1] >= start_thr:
                continue  # already in motion — not a fresh onset
            accel = per_frame[i] - per_frame[i - 1]
            if accel > best_accel:
                best_accel = accel
                best_i = i + 1  # 1-based
        return best_i

    @staticmethod
    def _direction(dx: float, dy: float) -> str:
        """Image-space direction of a motion vector (y points down)."""
        mag = (dx * dx + dy * dy) ** 0.5
        if mag < 1e-6:
            return "in place"
        vert = "up" if dy < 0 else "down"
        horiz = "left" if dx < 0 else "right"
        ax, ay = abs(dx), abs(dy)
        if ax > 2 * ay:
            return horiz
        if ay > 2 * ax:
            return vert
        return f"{vert}-{horiz}"

    def _describe(
        self,
        source: str,
        per_frame: List[float],
        states: List[str],
        vecs: Optional[List[Optional[dict]]],
    ) -> str:
        """One- or two-sentence objective motion summary fed to the LLM."""
        n = len(per_frame)
        active = [i for i, s in enumerate(states) if s != "still"]
        if not active:
            return "Hands stay essentially still across the window (no significant movement)."
        lo, hi = active[0] + 1, active[-1] + 1  # 1-based
        peak = max(range(n), key=lambda i: per_frame[i])
        span = f"frames {lo}-{hi}" if hi > lo else f"frame {lo}"

        if vecs is not None:  # skeleton: real wrist tracking
            out = [
                f"Pose tracking: wrist motion is concentrated in {span} "
                f"({len(active)}/{n} frames)."
            ]
            if peak < len(vecs) and vecs[peak]:
                v = vecs[peak]
                out.append(
                    f"Strongest at f{peak + 1}: a hand on the {v['side']} of the "
                    f"frame moves {self._direction(v['dx'], v['dy'])} "
                    f"(normalized {per_frame[peak]:.2f})."
                )
                ndx = sum(vecs[i]["dx"] for i in active if vecs[i])
                ndy = sum(vecs[i]["dy"] for i in active if vecs[i])
                out.append(f"Net hand path over the window: {self._direction(ndx, ndy)}.")
            return " ".join(out)

        # framediff fallback: only coarse whole-frame motion, no direction
        return (
            f"Frame-difference motion (no skeleton): activity concentrated in "
            f"{span} ({len(active)}/{n} frames), peak at f{peak + 1} "
            f"({per_frame[peak]:.2f}); hand direction unavailable."
        )

    def _summarize(
        self,
        source: str,
        per_frame: List[float],
        ok: bool,
        still_thr: float,
        start_thr: float,
        vecs: Optional[List[Optional[dict]]] = None,
        points: Optional[List[dict]] = None,
        base_sw: Optional[float] = None,
    ) -> dict:
        per_frame = self._smooth(per_frame)
        per_frame = [round(float(v), 4) for v in per_frame]
        states = [_state(v, still_thr, start_thr) for v in per_frame]
        max_change = max(per_frame) if per_frame else 0.0
        start_frame = self._detect_start(per_frame, still_thr, start_thr)
        return {
            "source": source,
            "ok": ok,
            "per_frame": per_frame,
            "states": states,
            "max_change": round(max_change, 4),
            "start_frame": start_frame,
            "description": self._describe(source, per_frame, states, vecs),
            "points": points,      # raw px keypoints per frame (skeleton only)
            "base_sw": base_sw,    # shoulder-width normalizer in px
        }

    def _empty(self, source: str) -> dict:
        return {
            "source": source,
            "ok": False,
            "per_frame": [],
            "states": [],
            "max_change": 0.0,
            "start_frame": 0,
            "description": "",
        }


_analyzer: Optional[MotionAnalyzer] = None


def get_analyzer() -> MotionAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = MotionAnalyzer()
    return _analyzer
