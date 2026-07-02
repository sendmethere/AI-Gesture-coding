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

We decode ONLY the analyzed [t0, t1] range ourselves and hand the waveform to
Whisper. Passing the video path instead makes faster-whisper decode the WHOLE
audio track before it applies clip_timestamps — on a 20-minute lecture that is
minutes of wasted decoding just to transcribe a 60-second window.

Transcripts are cached as JSON per (video, model, language, time-range) so
re-running analysis on the same clip is instant.
"""
import hashlib
import json
from pathlib import Path
from typing import Callable, List, Optional

from .paths import TRANSCRIPTS_DIR

SAMPLE_RATE = 16000  # Whisper input rate


def _decode_range(video_path: str, t0: float, t1: float):
    """Decode mono float32 audio for [t0, t1] (absolute secs) via PyAV.

    Returns (samples, base) where `samples` is a 16 kHz numpy array and `base`
    is the absolute video time of sample 0 (whisper times are relative to it).
    Only this range is decoded, so cost scales with the window, not the video.
    """
    import av
    import numpy as np

    container = av.open(video_path)
    try:
        stream = container.streams.audio[0]
    except (IndexError, KeyError):
        container.close()
        return np.zeros(0, dtype=np.float32), t0
    # Seek is keyframe-based; land a bit before t0 and keep frames overlapping.
    container.seek(int(max(0.0, t0 - 0.5) * av.time_base))
    resampler = av.AudioResampler(format="flt", layout="mono", rate=SAMPLE_RATE)
    chunks, base = [], None
    try:
        for frame in container.decode(stream):
            if frame.pts is None:
                continue
            ts = float(frame.pts * frame.time_base)
            if ts > t1:
                break
            dur = frame.samples / frame.sample_rate if frame.sample_rate else 0.0
            if ts + dur < t0:
                continue  # entirely before the window
            if base is None:
                base = ts
            for rf in resampler.resample(frame):
                chunks.append(rf.to_ndarray().reshape(-1))
    finally:
        container.close()
    if not chunks:
        return np.zeros(0, dtype=np.float32), t0
    return np.concatenate(chunks).astype(np.float32), (base if base is not None else t0)


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

        # Decode ONLY [t0, t1] ourselves; whisper times come back relative to the
        # clip start, so we shift them by `base` to restore absolute video time.
        audio, base = _decode_range(video_path, t0, t1)
        if audio.size == 0:
            self._save_cache(video_path, t0, t1, [])
            return []
        segments, _info = self.model.transcribe(
            audio,
            language=self.language or None,
            word_timestamps=True,
            vad_filter=True,   # now honored (only ignored when clip_timestamps set)
            beam_size=1,       # ponytail: greedy; STT is context only, not a result
        )
        out: List[dict] = []
        for s in segments:  # generator — iterating drives the actual work
            words = []
            for w in (s.words or []):
                words.append(
                    {
                        "start": round(float(w.start) + base, 3),
                        "end": round(float(w.end) + base, 3),
                        "word": w.word.strip(),
                    }
                )
            out.append(
                {
                    "start": round(float(s.start) + base, 3),
                    "end": round(float(s.end) + base, 3),
                    "text": s.text.strip(),
                    "words": words,
                }
            )
            if progress:
                progress(float(s.end) + base)
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
