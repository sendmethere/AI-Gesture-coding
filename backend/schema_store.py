"""Load / save the user-editable gesture classification schema.

Per plan.md section 5: the gesture system must NOT be hardcoded. Users edit
config/gesture_schema.json freely; changes are picked up on reload / restart.
"""
import json
from typing import List

from .paths import SCHEMA_PATH, CONFIG_DIR

# McNeill's gesture typology (plan.v2 §6.1). GT-N (no gesture) is represented by
# an empty list, so it is not a selectable code here.
DEFAULT_SCHEMA = {
    "gestures": [
        {"name": "GT-D", "description": "Deictic (지시적): a fingertip or hand extends toward a specific direction or target and holds (pointing)."},
        {"name": "GT-I", "description": "Iconic (상징적): a circular or curved path that imitates the shape or form of a concrete object."},
        {"name": "GT-M", "description": "Metaphoric (은유적): gives spatial form/motion to an ABSTRACT idea you can name — e.g. weighing two options like scales, placing past/future or choices left vs right, a rising motion for 'increase', cupped hands as an abstract container. STRICT: do NOT use for plain directional motion that is only rhythmic emphasis (GT-B), for pointing (GT-D), for tracing a concrete object's real shape (GT-I), or for incidental motion. If you cannot state the specific abstract meaning, do not code GT-M."},
        {"name": "GT-B", "description": "Beat (박자적): short, repeated movements with a steady rhythm, in time with speech (emphasis, not meaning)."},
        {"name": "GT-E", "description": "Emblematic (관습적): a culturally standardized conventional pattern (e.g., raising a hand, thumbs-up, OK sign)."},
        {"name": "GT-X", "description": "Unclassifiable (판별 불가): hand or arm movement is present but its gesture type cannot be determined."},
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
