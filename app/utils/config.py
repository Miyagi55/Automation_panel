# app/utils/config.py
import os
import sys
from pathlib import Path

import __main__

# Configurable CONSTANTS
ACCOUNT_TEST_BROWSER_TIMEOUT_SECONDS = 60  #  Edit as needed
LINK_LOGIN = "https://www.facebook.com/login"
OS = os.name  # 'nt' for Windows, 'posix' for Linux/Mac


def get_project_root() -> Path:
    if getattr(sys, "frozen", False):
        # Running in PyInstaller bundle
        return Path(sys.executable).resolve().parent
    else:
        # Running in development
        return Path(__main__.__file__).resolve().parent


ROOT = get_project_root()
DATA_DIR = ROOT / "data"
SESSIONS = DATA_DIR / "sessions"
LOG_DIR = ROOT / "logs"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"

PLAYWRIGHT_DIR = os.path.join(
    os.path.expanduser("~"), "AppData", "Local", "ms-playwright"
)
