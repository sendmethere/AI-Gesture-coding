"""Teacher detection / cropping (plan.md Step 3).

Uses YOLO (ultralytics) when available to find the most prominent person and
crop to it. If ultralytics / weights are unavailable, gracefully falls back to
returning the full frame so the pipeline still works.
"""
from typing import Optional

import numpy as np


class TeacherDetector:
    def __init__(self, model_name: str = "yolov8n.pt"):
        self.available = False
        self.model = None
        try:
            from ultralytics import YOLO  # type: ignore

            self.model = YOLO(model_name)
            self.available = True
        except Exception as e:  # pragma: no cover - depends on optional dep
            self._reason = str(e)

    def status(self) -> str:
        return "yolo" if self.available else "fallback(full-frame)"

    def crop_teacher(self, frame_bgr: np.ndarray, pad: float = 0.10) -> np.ndarray:
        """Return a crop around the largest detected person, else the frame."""
        if not self.available or self.model is None:
            return frame_bgr
        try:
            results = self.model(frame_bgr, classes=[0], verbose=False)
            best = None
            best_area = 0.0
            for r in results:
                boxes = getattr(r, "boxes", None)
                if boxes is None:
                    continue
                for box in boxes.xyxy.tolist():
                    x1, y1, x2, y2 = box
                    area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
                    if area > best_area:
                        best_area = area
                        best = (x1, y1, x2, y2)
            if best is None:
                return frame_bgr
            h, w = frame_bgr.shape[:2]
            x1, y1, x2, y2 = best
            px = (x2 - x1) * pad
            py = (y2 - y1) * pad
            x1 = int(max(0, x1 - px))
            y1 = int(max(0, y1 - py))
            x2 = int(min(w, x2 + px))
            y2 = int(min(h, y2 + py))
            if x2 <= x1 or y2 <= y1:
                return frame_bgr
            return frame_bgr[y1:y2, x1:x2]
        except Exception:
            return frame_bgr


_detector: Optional[TeacherDetector] = None


def get_detector() -> TeacherDetector:
    global _detector
    if _detector is None:
        _detector = TeacherDetector()
    return _detector
