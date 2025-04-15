from pathlib import Path

ROOT = (
    Path(__file__).resolve().parent.parent.parent
)  # TODO: temp fix, improve this later
DATA_DIR = ROOT / "data"
SESSIONS = DATA_DIR / "sessions"
LOG_DIR = DATA_DIR / "logs"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"
