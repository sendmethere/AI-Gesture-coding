"""Persist LLM / analysis settings to config/settings.json.

NOTE: the API key is stored locally for convenience (this is a single-user
desktop research tool). config/settings.json is git-ignored.
"""
import json

from .paths import SETTINGS_PATH, CONFIG_DIR

DEFAULTS = {
    "provider": "mock",          # mock | openai | anthropic | gemini
    "model": "",
    "api_key": "",
    "interval": 0.5,             # seconds between extracted frames
    "segment_frames": 6,         # frames combined per strip (6 * 0.5s = 3s)
    "start_offset": 0,           # start analysis at this many seconds into the video
    "max_duration": 60,          # analyze only N seconds from start_offset (0 = to end)
    "min_confidence": 0.0,       # below this, the segment is forced to None (0 = off)
    "include_confidence": True,
    "save_strips": True,
}

ALLOWED = set(DEFAULTS.keys())


def load_settings() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            return {**DEFAULTS, **{k: v for k, v in data.items() if k in ALLOWED}}
        except Exception:
            pass
    return dict(DEFAULTS)


def save_settings(patch: dict) -> dict:
    cur = load_settings()
    for k, v in patch.items():
        if k in ALLOWED:
            cur[k] = v
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(cur, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return cur


def public_settings() -> dict:
    """Settings safe to send to the frontend (api_key presence only)."""
    s = load_settings()
    out = dict(s)
    out["has_api_key"] = bool(s.get("api_key"))
    out.pop("api_key", None)
    return out
