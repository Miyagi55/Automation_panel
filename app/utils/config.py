# app/utils/config.py
from pathlib import Path


#Configurable CONSTANTS
ACCOUNT_TEST_BROWSER_TIMEOUT_SECONDS = 60  #  Edit as needed
LINK_LOGIN = "https://www.facebook.com/login"

def get_project_root() -> Path:
    """Find the project root by looking for a known file (e.g., pyproject.toml)."""
    current = Path(__file__).resolve()
    while current != current.parent:  # Stop at filesystem root
        if (current / "pyproject.toml").exists():  # Or another marker file
            return current
        current = current.parent
    raise RuntimeError("Could not find project root")

ROOT = get_project_root()
DATA_DIR = ROOT / "data"
SESSIONS = DATA_DIR / "sessions"
LOG_DIR = DATA_DIR / "logs"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"


