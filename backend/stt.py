"""Speech-to-text transcription (plan.v2 §1.2).

Transcribes the analyzed portion of a video into timestamped segments + words so
each analysis window can be annotated with the sentence(s)/words the teacher is
speaking at that moment. This is what later enables gesture-speech synchronization
analysis (plan §6.3 SY codes, §10 auto-alignment).

Engine: faster-whisper (CTranslate2 Whisper). It is an OPTIONAL heavy dependency
— if it (or its weights) cannot be loaded, STT is simply unavailable and the rest
of the pipeline runs unchanged (same graceful-fallback pattern as detector.py /
motion.py). Audio is decoded straight from the video container via PyAV, so no
external ffmpeg binary is required.

Transcripts are cached as JSON per (video, model, language, time-range) so
re-running analysis on the same clip is instant.
"""
import hashlib
import json
from pathlib import Path
from typing import Callable, List, Optional

from .paths import TRANSCRIPTS_DIR


class Transcriber:
    def __init__(self, model_size: str = "base", language: str = ""):
        self.model_size = model_size or "base"
        self.language = language or ""  # "" = auto-detect
        self.available = False
        self.model = None
        self._reason = ""
        try:
            from faster_whisper import WhisperModel  # type: ignore

            # int8 on CPU is the fast/light default; good enough for research use.
            self.model = WhisperModel(
                self.model_size, device="cpu", compute_type="int8"
            )
            self.available = True
        except Exception as e:  # pragma: no cover - optional dep
            self._reason = str(e)

    def status(self) -> str:
        return f"whisper:{self.model_size}" if self.available else "off"

    # ----- transcription ------------------------------------------------- #
    def transcribe_range(
        self,
        video_path: str,
        t0: float,
        t1: float,
        progress: Optional[Callable[[float], None]] = None,
    ) -> List[dict]:
        """Return timestamped segments for video time [t0, t1] (absolute secs).

        Each segment: {start, end, text, words:[{start,end,word}, ...]}.
        Results are cached on disk. Returns [] if STT is unavailable.
        """
        if not self.available or self.model is None:
            return []

        cached = self._load_cache(video_path, t0, t1)
        if cached is not None:
            if progress:
                progress(t1)
            return cached

        clip = f"{max(0.0, t0):.3f},{max(t0, t1):.3f}"
        segments, _info = self.model.transcribe(
            video_path,
            language=self.language or None,
            word_timestamps=True,
            vad_filter=True,
            clip_timestamps=clip,
        )
        out: List[dict] = []
        for s in segments:  # generator — iterating drives the actual work
            words = []
            for w in (s.words or []):
                words.append(
                    {
                        "start": round(float(w.start), 3),
                        "end": round(float(w.end), 3),
                        "word": w.word.strip(),
                    }
                )
            out.append(
                {
                    "start": round(float(s.start), 3),
                    "end": round(float(s.end), 3),
                    "text": s.text.strip(),
                    "words": words,
                }
            )
            if progress:
                progress(float(s.end))
        self._save_cache(video_path, t0, t1, out)
        return out

    # ----- caching ------------------------------------------------------- #
    def _cache_path(self, video_path: str, t0: float, t1: float) -> Path:
        stem = Path(video_path).stem
        key = f"{self.model_size}|{self.language}|{t0:.3f}|{t1:.3f}"
        h = hashlib.md5(key.encode()).hexdigest()[:10]
        return TRANSCRIPTS_DIR / stem / f"{h}.json"

    def _load_cache(self, video_path: str, t0: float, t1: float) -> Optional[List[dict]]:
        p = self._cache_path(video_path, t0, t1)
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None

    def _save_cache(self, video_path: str, t0: float, t1: float, data: List[dict]) -> None:
        p = self._cache_path(video_path, t0, t1)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Window slicing
# --------------------------------------------------------------------------- #
def speech_in_window(transcript: List[dict], t0: float, t1: float) -> str:
    """Words spoken during [t0, t1), joined into a string (plan §1.2).

    Prefers word-level timestamps for precision; falls back to any segment that
    overlaps the window when word timestamps are missing.
    """
    if not transcript:
        return ""
    words = []
    have_words = False
    for seg in transcript:
        for w in seg.get("words", []):
            have_words = True
            ws = w.get("start", seg["start"])
            if t0 <= ws < t1:
                words.append(w["word"])
    if have_words:
        return " ".join(words).strip()

    # No word timestamps: use overlapping segment text.
    parts = []
    for seg in transcript:
        if seg["end"] > t0 and seg["start"] < t1:
            parts.append(seg["text"])
    return " ".join(parts).strip()


_transcriber: Optional[Transcriber] = None
_key = None


def get_transcriber(model_size: str = "base", language: str = "") -> Transcriber:
    """Singleton, rebuilt only when the model/language selection changes."""
    global _transcriber, _key
    key = (model_size or "base", language or "")
    if _transcriber is None or _key != key:
        _transcriber = Transcriber(model_size=key[0], language=key[1])
        _key = key
    return _transcriber
