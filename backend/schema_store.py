"""Load / save the user-editable gesture classification schema.

Per plan.md section 5: the gesture system must NOT be hardcoded. Users edit
config/gesture_schema.json freely; changes are picked up on reload / restart.
"""
import json
from typing import List

from .paths import SCHEMA_PATH, CONFIG_DIR

DEFAULT_SCHEMA = {
    "gestures": [
        {"name": "Deictic", "description": "Pointing at a general object/location (screen=PointScreen, audience=PointAudience)"},
        {"name": "PointScreen", "description": "Pointing at a specific part of the screen, board, or material"},
        {"name": "PointAudience", "description": "Pointing at students/audience with hand or arm"},
        {"name": "Beat", "description": "Repeated rhythmic hand movements for emphasis"},
        {"name": "Iconic", "description": "Depicting an object's shape/motion with the hands"},
        {"name": "Metaphoric", "description": "Representing an abstract concept via space/form"},
        {"name": "Emblematic", "description": "Conventional symbolic gesture (thumbs-up, OK, etc.)"},
        {"name": "OpenPalm", "description": "Open palm presenting/opening (audience target = OpenPalmAudience)"},
        {"name": "OpenPalmAudience", "description": "Open palm toward the audience to offer the floor/invite"},
        {"name": "RaiseHand", "description": "Arm raised above the shoulder to draw attention/nominate"},
        {"name": "Writing", "description": "Writing/drawing on a board or whiteboard (board work)"},
        {"name": "LookAtScreen", "description": "Turning gaze/body to the screen or board without pointing"},
        {"name": "TurnBack", "description": "Turning one's back to the audience"},
        {"name": "Cohesive", "description": "Re-pointing at a prior target to link the discourse"},
        {"name": "Nodding", "description": "Nodding up and down to show agreement/affirmation"},
        {"name": "HeadShake", "description": "Shaking the head to show disagreement/negation"},
    ]
}


def load_schema() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if SCHEMA_PATH.exists():
        try:
            data = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("gestures"), list):
                return data
        except Exception:
            pass
    # Seed a default file the user can then edit.
    save_schema(DEFAULT_SCHEMA)
    return dict(DEFAULT_SCHEMA)


def save_schema(data: dict) -> dict:
    if not isinstance(data, dict) or not isinstance(data.get("gestures"), list):
        raise ValueError("schema must be an object with a 'gestures' list")
    cleaned = {"gestures": []}
    for g in data["gestures"]:
        name = str(g.get("name", "")).strip()
        if not name:
            continue
        cleaned["gestures"].append(
            {"name": name, "description": str(g.get("description", "")).strip()}
        )
    if not cleaned["gestures"]:
        raise ValueError("schema must contain at least one gesture with a name")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(
        json.dumps(cleaned, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return cleaned


def gesture_names(schema: dict) -> List[str]:
    return [g["name"] for g in schema.get("gestures", []) if g.get("name")]
