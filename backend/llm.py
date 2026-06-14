"""LLM Vision analysis (plan.md Step 5).

Sends a combined "strip" image plus the gesture schema to an LLM and parses a
strict-JSON response: {"gestures": [...], "confidence": 0.0-1.0}.

Providers: openai | anthropic | gemini | mock
The "mock" provider needs no API key and lets the whole app run end-to-end for
demos / testing.
"""
import base64
import json
import re
from typing import List

import requests

DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-6",
    "gemini": "gemini-1.5-flash",
    "mock": "mock-1",
}

TIMEOUT = 90


class LLMError(Exception):
    pass


def _check(r, provider: str):
    """Raise with the API's real error message (not just '400 Bad Request')."""
    if r.status_code >= 400:
        msg = r.text[:400]
        try:
            body = r.json()
            err = body.get("error")
            if isinstance(err, dict):
                msg = err.get("message") or msg
            elif isinstance(err, str):
                msg = err
        except Exception:
            pass
        raise LLMError(f"{provider} {r.status_code}: {msg}")
    return r


def build_prompt(schema: dict, speech: str = "") -> str:
    lines = []
    for g in schema.get("gestures", []):
        lines.append(f'- {g["name"]}: {g.get("description", "")}')
    catalog = "\n".join(lines)
    names = [g["name"] for g in schema.get("gestures", [])]

    speech_note = ""
    if speech:
        speech_note = (
            f'\nThe teacher is speaking during this segment: "{speech}"\n'
            "Use this speech only as CONTEXT to disambiguate the gesture (e.g. a "
            "deictic point vs an iconic shape); do not code a gesture that is not "
            "physically performed just because the words suggest one.\n"
        )

    # Detailed decision guide for McNeill GT-* schemas. Skipped automatically if
    # the user has swapped in a non-GT schema (falls back to the generic rules).
    is_mcneill = any(str(n).upper().startswith("GT-") for n in names)
    guide = ""
    if is_mcneill:
        guide = (
            "\nDecision guide — work through it in order:\n"
            "1. Is there a clear, deliberate, communicative hand/arm gesture? "
            "If the motion is incidental, transitional, fidgeting, adjusting "
            "clothes/hair, or just holding an object, return [] (GT-N).\n"
            "2. If yes, choose the type by what the hands actually do:\n"
            "   • GT-D (Deictic): an extended finger/hand/arm aims at a specific "
            "target or direction and briefly holds.\n"
            "   • GT-I (Iconic): the hands trace the LITERAL shape, size, or "
            "physical motion of a CONCRETE object (a circle, a slope, a box).\n"
            "   • GT-M (Metaphoric): the movement maps a NAMEABLE ABSTRACT idea "
            "onto space — comparing/weighing options, a timeline or sequence laid "
            "in space, growth/decline as up/down, an idea held in a 'container'. "
            "You must be able to state the abstract meaning in words.\n"
            "   • GT-B (Beat): short, repeated, low-amplitude strokes that keep "
            "rhythm with speech for emphasis; they carry no pictorial meaning.\n"
            "   • GT-E (Emblematic): a fixed, culturally conventional sign "
            "(raised open palm = stop/attention, thumbs-up, OK, raising a hand).\n"
            "   • GT-X: a clear gesture is present but its type is genuinely "
            "ambiguous.\n"
            "3. METAPHORIC IS THE STRICTEST CATEGORY. Only code GT-M when you can "
            "name the specific abstract concept being spatialized. Plain "
            "directional motion is NOT metaphoric by itself: if it is rhythmic "
            "emphasis use GT-B, if it depicts a real object use GT-I, and if you "
            "cannot name an abstract meaning use GT-X or return [] — never default "
            "to GT-M.\n"
        )

    return (
        "You are an expert coder of teacher gestures in microteaching videos, "
        "using McNeill's gesture typology.\n"
        "The image is a horizontal strip of sequential video frames of one "
        "teacher, spaced a fraction of a second apart, read left to right.\n"
        "A colored bar under each frame may indicate measured hand motion: "
        "gray=still, yellow=preparing, green=gesture start, blue=in motion; the "
        "number is the normalized hand displacement. Use it to locate where a "
        "gesture actually happens, but base the CODE on what the hands do.\n"
        + speech_note
        + "\nClassify the teacher gesture(s) visible across this segment using "
        "ONLY the following categories:\n"
        f"{catalog}\n"
        + guide
        + "\nRules:\n"
        f"- Use only these exact names: {names}\n"
        "- If there is no meaningful, communicative hand/arm gesture, return an "
        "empty list [] (this is GT-N / no gesture). Do not guess.\n"
        "- Use GT-X only when a gesture is clearly present but you cannot "
        "determine its type.\n"
        "- Code GT-B (Beat) only for clearly rhythmic, repeated movements used for "
        "emphasis — not for small, incidental, transitional, or resting motion.\n"
        "- Assign multiple codes only when several distinct gestures clearly "
        "co-occur in the segment.\n"
        "- Respond with STRICT JSON only, no prose, no markdown fences:\n"
        '{"gestures": ["GT-D", ...], "confidence": 0.0}\n'
        "- confidence is your overall certainty for this segment (0.0-1.0)."
    )


def _parse_json(text: str) -> dict:
    if not text:
        return {"gestures": [], "confidence": 0.0}
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if m:
        cleaned = m.group(0)
    try:
        data = json.loads(cleaned)
    except Exception:
        return {"gestures": [], "confidence": 0.0, "raw": text}
    gestures = data.get("gestures", [])
    if not isinstance(gestures, list):
        gestures = [str(gestures)]
    gestures = [str(g) for g in gestures]
    try:
        conf = float(data.get("confidence", 0.0))
    except Exception:
        conf = 0.0
    return {"gestures": gestures, "confidence": max(0.0, min(1.0, conf))}


def _filter_to_schema(result: dict, valid_names: List[str]) -> dict:
    valid = {n.lower(): n for n in valid_names}
    out = []
    for g in result.get("gestures", []):
        key = str(g).strip().lower()
        if key in valid and valid[key] not in out:
            out.append(valid[key])
    result["gestures"] = out
    return result


# --------------------------------------------------------------------------- #
# Providers
# --------------------------------------------------------------------------- #
def _mock(strip_png: bytes, schema: dict, seg_index: int) -> dict:
    names = [g["name"] for g in schema.get("gestures", [])]
    if not names:
        return {"gestures": [], "confidence": 0.0}
    conf = round(0.7 + ((seg_index * 7) % 30) / 100.0, 2)
    # Realistic: most segments have no codeable gesture (None / []).
    r = seg_index % 5
    if r in (0, 1, 3):  # ~60% empty
        return {"gestures": [], "confidence": conf}
    pick = [names[(seg_index * 3) % len(names)]]
    if r == 4 and len(names) > 1:
        pick.append(names[(seg_index * 3 + 2) % len(names)])
    return {"gestures": pick, "confidence": conf}


def _openai(strip_png, schema, api_key, model, speech="") -> dict:
    b64 = base64.b64encode(strip_png).decode()
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    # Newer models (gpt-5 / o-series) require `max_completion_tokens` and only
    # accept the default temperature, so we use the modern param and drop
    # temperature if the API rejects it.
    base = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": build_prompt(schema, speech)},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ],
        "max_completion_tokens": 800,
    }
    r = requests.post(url, headers=headers, json={**base, "temperature": 0}, timeout=TIMEOUT)
    if r.status_code == 400 and "temperature" in (r.text or "").lower():
        r = requests.post(url, headers=headers, json=base, timeout=TIMEOUT)
    _check(r, "openai")
    text = r.json()["choices"][0]["message"]["content"]
    return _parse_json(text)


def _anthropic(strip_png, schema, api_key, model, speech="") -> dict:
    b64 = base64.b64encode(strip_png).decode()
    payload = {
        "model": model,
        "max_tokens": 800,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": build_prompt(schema, speech)},
                ],
            }
        ],
    }
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json=payload,
        timeout=TIMEOUT,
    )
    _check(r, "anthropic")
    parts = r.json().get("content", [])
    text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
    return _parse_json(text)


def _gemini(strip_png, schema, api_key, model, speech="") -> dict:
    b64 = base64.b64encode(strip_png).decode()
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": build_prompt(schema, speech)},
                    {"inline_data": {"mime_type": "image/png", "data": b64}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 800},
    }
    r = requests.post(url, json=payload, timeout=TIMEOUT)
    _check(r, "gemini")
    cand = r.json()["candidates"][0]["content"]["parts"]
    text = "".join(p.get("text", "") for p in cand)
    return _parse_json(text)


def analyze_strip(
    provider: str,
    api_key: str,
    model: str,
    strip_png: bytes,
    schema: dict,
    seg_index: int = 0,
    speech: str = "",
) -> dict:
    provider = (provider or "mock").lower()
    model = model or DEFAULT_MODELS.get(provider, "")
    valid_names = [g["name"] for g in schema.get("gestures", [])]

    if provider == "mock":
        result = _mock(strip_png, schema, seg_index)
    elif provider == "openai":
        result = _openai(strip_png, schema, api_key, model, speech)
    elif provider == "anthropic":
        result = _anthropic(strip_png, schema, api_key, model, speech)
    elif provider == "gemini":
        result = _gemini(strip_png, schema, api_key, model, speech)
    else:
        raise ValueError(f"unknown provider: {provider}")

    return _filter_to_schema(result, valid_names)
