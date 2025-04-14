from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data"
SESSIONS = DATA_DIR / "sessions"
LOG_DIR = DATA_DIR / "logs"
