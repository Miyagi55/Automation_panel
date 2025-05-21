# app/utils/config.py
import json
import os
import sys
from pathlib import Path

import __main__

# Configurable CONSTANTS

ACCOUNT_TEST_BROWSER_TIMEOUT_SECONDS = 60  #  Edit as needed
LINK_LOGIN = "https://www.facebook.com/login"
OS = os.name  # 'nt' for Windows, 'posix' for Linux/Mac

USER_APP_DIR = Path.home() / "Automation_Panel"
CONFIG_FILE_PATH = USER_APP_DIR / "config.json"


def get_project_root() -> Path:
    if getattr(sys, "frozen", False):
        # Running in PyInstaller bundle
        return Path(sys.executable).resolve().parent
    else:
        # Running in development
        return Path(__main__.__file__).resolve().parent


def get_app_config_path() -> Path:
    """Ensures the app config directory and default config.json exist, returns path to config.json."""
    os.makedirs(USER_APP_DIR, exist_ok=True)
    if not CONFIG_FILE_PATH.exists():
        # Create a default config if it doesn't exist
        default_data_dir = USER_APP_DIR / "data"
        os.makedirs(default_data_dir, exist_ok=True)
        with open(CONFIG_FILE_PATH, "w") as f:
            json.dump({"data_dir": str(default_data_dir)}, f, indent=4)
    return CONFIG_FILE_PATH


def get_data_dir() -> Path:
    """Get the data directory path from config.json or use default user-specific path."""
    config_path = get_app_config_path()  # Ensures config.json exists

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            data_dir_str = config.get("data_dir")
            if data_dir_str:
                data_dir = Path(data_dir_str)
                # Ensure it's an absolute path, if not, it might be an old relative config.
                # For simplicity, we now always store absolute paths.
                if not data_dir.is_absolute():
                    # This case should ideally not happen with new configs,
                    # but handle for robustness if an old relative path was somehow set.
                    # We will resolve it relative to USER_APP_DIR for safety.
                    data_dir = USER_APP_DIR / data_dir_str
            else:  # Fallback if "data_dir" is missing in config
                data_dir = USER_APP_DIR / "data"
    except Exception as e:
        print(
            f"Error reading config.json or data_dir not set: {str(e)}. Using default data directory."
        )
        data_dir = USER_APP_DIR / "data"

    os.makedirs(data_dir, exist_ok=True)
    return data_dir


# File Paths:
ROOT = get_project_root()  # Remains project root for development/PyInstaller structure
APP_CONFIG_PATH = get_app_config_path()  # Path to config.json in user directory
DATA_DIR = get_data_dir()  # User-configurable data directory
LOG_DIR = USER_APP_DIR / "logs"  # Logs in user directory
SESSIONS = DATA_DIR / "sessions"  # Sessions within the current DATA_DIR
ACCOUNTS_FILE = DATA_DIR / "accounts.json"  # Accounts within the current DATA_DIR

# Create necessary directories
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(
    SESSIONS, exist_ok=True
)  # SESSIONS depends on DATA_DIR, so it's created after DATA_DIR is resolved

PLAYWRIGHT_DIR = Path.home() / "AppData" / "Local" / "ms-playwright"


# DELAYS (a: float, b: float)
SESSION_RETRY_DELAY = (2.0, 2.0)
LOGIN_POST_LOAD_DELAY = (5.0, 5.0)
BROWSER_MANAGER_PROGRESS_DELAY = (0.5, 0.5)
LIKE_ACTION_DELAY_RANGE = (0.5, 2.0)
COMMENT_ACTION_DELAY_RANGE = (0.5, 5.0)

# Add automation handler delay ranges
AUTOMATION_ACTION_DELAY_RANGE = (2.0, 5.0)
AUTOMATION_ACCOUNT_DELAY_RANGE = (5.0, 10.0)
