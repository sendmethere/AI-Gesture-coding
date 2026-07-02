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
        {"name": "GT-D", "description": "Deictic (지시적): concrete or abstract pointing — an extended finger, hand, arm, or pen/pointer aims at a specific target or direction. Always context-sensitive: it explicitly directs attention to the visual information that speech is currently referring to. Examples: pointing at a word or figure on the board, at a student, off to 'over there', or an abstract point to a location standing in for a referent. NOT: a hand that traces a shape or sweeps without aiming (→ GT-I/GT-M); incidental hand raises or reaching for an object."},
        {"name": "GT-I", "description": "Iconic (도상적): shows what is being said 'just in time' and pictorially — the hands depict the literal shape, SIZE, or physical motion of a CONCRETE object/event, with a tight semantic link between the speech and the simultaneous hand movement. Examples: tracing a circle or box, hands spreading apart to show something large or drawing together to show something small, widening/hunching the body to show a big vs tiny object, miming pouring or a bouncing ball. Note: a concrete object's physical size is GT-I; an ABSTRACT magnitude with no real object (e.g. a 'big' problem, great importance) is GT-M. NOT: pointing at a target (→ GT-D); rhythmic beats that form no shape (→ GT-B); movement with no concrete object actually depicted."},
        {"name": "GT-M", "description": "Metaphoric (은유적): like an iconic gesture, but what is depicted is an ABSTRACT idea rather than a physically present object — the hands carry an image that stands for a concept, aiming to make an invisible idea visible through abstraction. Common in teaching: presenting/offering an idea on an open palm or cupped hands (the 'conduit'), placing contrasting ideas or 'on one hand … on the other' in left-vs-right space, laying steps or a timeline out across space, up/forward = more/increase/future and down/back = less/decrease/past, weighing two options like a balance, or expansive hands for a 'big'/important idea. Code GT-M only when the image-to-idea mapping is clear and deliberate (you can say what idea the space stands for). NOT: pointing (→ GT-D); depicting a REAL object's shape/size/motion (→ GT-I); rhythmic emphasis with no image (→ GT-B); when the mapping is weak, vague, or uncertain (→ GT-B/GT-X/no code)."},
        {"name": "GT-B", "description": "Beat (박자적): any hand movement timed to the rhythm of speech — non-pictorial gestures that emphasize the linguistic information rather than depict anything. Typically short, quick, repeated strokes: raising and lowering the hand, tapping or tapping-down on stressed words, small repeated chops while listing items. Though the least conspicuous gesture, recurring beats across the talk not only support the speech but also draw attention to the speaker. NOT: a gesture that aims at a target (→ GT-D) or depicts a shape/idea (→ GT-I/GT-M); steady holding or a non-rhythmic one-off motion."},
        {"name": "GT-X", "description": "Unclassifiable (판별 불가): hand or arm movement is clearly present but its gesture type genuinely cannot be determined. NOT: a lazy default when one of GT-D/I/M/B clearly fits; and NOT for the absence of gesture (no meaningful movement → return an empty list, which is GT-N)."},
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
