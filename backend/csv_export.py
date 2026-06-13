"""CSV export (plan.md section 9)."""
import csv
import io
import json
from typing import List

from .paths import RESULT_CSV_PATH, RESULTS_DIR


def results_to_csv(results: List[dict], include_confidence: bool = False) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    if include_confidence:
        writer.writerow(["no", "timestamp", "gesture", "confidence"])
    else:
        writer.writerow(["no", "timestamp", "gesture"])
    for r in results:
        gesture = json.dumps(r.get("gesture", []), ensure_ascii=False)
        if include_confidence:
            writer.writerow(
                [r.get("no"), r.get("timestamp"), gesture, r.get("confidence", "")]
            )
        else:
            writer.writerow([r.get("no"), r.get("timestamp"), gesture])
    return buf.getvalue()


def save_csv(results: List[dict], include_confidence: bool = False) -> str:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    text = results_to_csv(results, include_confidence)
    RESULT_CSV_PATH.write_text(text, encoding="utf-8")
    return str(RESULT_CSV_PATH)
