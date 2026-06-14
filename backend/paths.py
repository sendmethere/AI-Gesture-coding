"""Central place for project directory layout (see plan.md section 10)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

VIDEOS_DIR = ROOT / "videos"
CROPS_DIR = ROOT / "crops"
STRIPS_DIR = ROOT / "strips"
RESULTS_DIR = ROOT / "results"
CONFIG_DIR = ROOT / "config"
LOGS_DIR = ROOT / "logs"
FRONTEND_DIR = ROOT / "frontend"
TRANSCRIPTS_DIR = ROOT / "transcripts"

SCHEMA_PATH = CONFIG_DIR / "gesture_schema.json"
SETTINGS_PATH = CONFIG_DIR / "settings.json"
RESULT_CSV_PATH = RESULTS_DIR / "gesture_result.csv"


def ensure_dirs() -> None:
    for d in (
        VIDEOS_DIR, CROPS_DIR, STRIPS_DIR, RESULTS_DIR,
        CONFIG_DIR, LOGS_DIR, TRANSCRIPTS_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)
