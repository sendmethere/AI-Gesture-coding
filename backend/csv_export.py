"""CSV export (plan.md section 9)."""
import csv
import io
import json
from typing import List

from .paths import RESULT_CSV_PATH, RESULTS_DIR


def results_to_csv(results: List[dict], include_confidence: bool = False) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    # Include grading metadata columns only if the run produced them (plan.v2).
    include_meta = any(r.get("grade") for r in results)
    include_speech = any(r.get("speech") for r in results)

    header = ["no", "timestamp", "gesture"]
    if include_confidence:
        header.append("confidence")
    if include_meta:
        header += ["grade", "motion", "source", "review_flag"]
    if include_speech:
        header.append("speech")
    writer.writerow(header)

    for r in results:
        row = [
            r.get("no"),
            r.get("timestamp"),
            json.dumps(r.get("gesture", []), ensure_ascii=False),
        ]
        if include_confidence:
            row.append(r.get("confidence", ""))
        if include_meta:
            row += [
                r.get("grade", ""),
                r.get("motion", ""),
                r.get("source", "") or "",
                1 if r.get("review_flag") else 0,
            ]
        if include_speech:
            row.append(r.get("speech", "") or "")
        writer.writerow(row)
    return buf.getvalue()


def save_csv(
    results: List[dict], include_confidence: bool = False, name: str = ""
) -> str:
    """Write the CSV. `name` (a bare filename) overrides the default path."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    text = results_to_csv(results, include_confidence)
    target = (RESULTS_DIR / name) if name else RESULT_CSV_PATH
    target.write_text(text, encoding="utf-8")
    return str(target)
