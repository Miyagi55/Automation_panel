"""
Browser manager for handling Playwright browser sessions.
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional


class BrowserManager:
    """
    Manages browser automation using Playwright.
    Handles browser sessions, authentication, and actions.
    """

    _instance = None
    _webdriver_path = None
    _project_root = Path(__file__).resolve().parent.parent.parent
    _sessions_base_dir = str(_project_root / "sessions")

    def __new__(cls):
        """Singleton pattern to ensure only one browser manager exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_path(print)
            # Ensure the sessions base directory exists
            os.makedirs(cls._sessions_base_dir, exist_ok=True)
        return cls._instance

    def _initialize_path(self, log_func: Callable[[str], None]) -> None:
        """Set webdriver path if it exists."""
        home_dir = os.path.expanduser("~")
        path = os.path.join(home_dir, "AppData", "Local", "ms-playwright")

        if not os.path.exists(path):
            log_func(f"Playwright path not found: {path}")
            return

        chromium_dir = self._find_chromium_dir(path, log_func)
        if chromium_dir and self._verify_chromium_executable(chromium_dir, log_func):
            self._webdriver_path = path
            log_func(f"Webdriver path initialized: {self._webdriver_path}")

    def _find_chromium_dir(
        self, base_path: str, log_func: Callable[[str], None]
    ) -> Optional[str]:
        """Find the Chromium directory in the webdriver path."""
        try:
            for subdir in os.listdir(base_path):
                chromium_path = os.path.join(base_path, subdir, "chrome-win")
                if os.path.exists(chromium_path):
                    return os.path.join(base_path, subdir)
            log_func("Chromium directory not found")
            return None
        except Exception as e:
            log_func(f"Error finding Chromium directory: {str(e)}")
            return None

    def _verify_chromium_executable(
        self, chromium_dir: str, log_func: Callable[[str], None]
    ) -> bool:
        """Verify the Chromium executable exists."""
        chromium_path = os.path.join(chromium_dir, "chrome-win", "chrome.exe")
        exists = os.path.exists(chromium_path)
        if not exists:
            log_func(f"Chromium executable not found at: {chromium_path}")
        return exists

    @property
    def webdriver_path(self) -> Optional[str]:
        """Get the current webdriver path."""
        return self._webdriver_path

    def install_webdrivers(
        self,
        log_func: Callable[[str], None],
        update_progress: Callable[[str, float], None],
    ) -> bool:
        """Install Playwright webdrivers with progress updates."""
        log_func("Starting webdriver installation...")
        update_progress("Installing...", 0.1)

        try:
            result = self._run_playwright_install(log_func)
            if not result:
                update_progress("Installation failed", 1.0)
                return False
        except Exception as e:
            log_func(f"Installation exception: {str(e)}")
            update_progress(f"Error: {str(e)}", 1.0)
            return False

        # Simulate download progress
        self._simulate_progress(update_progress)

        # Verify installation
        home_dir = os.path.expanduser("~")
        self._webdriver_path = os.path.join(
            home_dir, "AppData", "Local", "ms-playwright"
        )

        chromium_dir = self._find_chromium_dir(self._webdriver_path, log_func)
        if not chromium_dir or not self._verify_chromium_executable(
            chromium_dir, log_func
        ):
            log_func("Invalid or missing webdriver installation")
            update_progress("Error: Installation incomplete", 1.0)
            return False

        update_progress("Complete!", 1.0)
        log_func(f"Webdrivers installed at: {self._webdriver_path}")
        return True

    def _run_playwright_install(self, log_func: Callable[[str], None]) -> bool:
        """Run the playwright install command."""
        try:
            process = subprocess.run(
                ["playwright", "install", "--with-deps"],
                capture_output=True,
                text=True,
                check=True,
            )
            log_func(f"Installation output: {process.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            log_func(f"Installation failed: {e.stderr}")
            return False

    def _simulate_progress(self, update_progress: Callable[[str, float], None]) -> None:
        """Simulate download progress for the UI."""
        for i in range(1, 10):
            time.sleep(0.5)
            update_progress("Downloading...", 0.1 + i * 0.09)

    def get_session_dir(self, account_id: str) -> str:
        """Get the session directory for a given account ID."""
        session_dir = os.path.join(self._sessions_base_dir, f"session_{account_id}")
        os.makedirs(session_dir, exist_ok=True)
        return session_dir

    def get_chromium_executable(self, log_func: Callable[[str], None]) -> Optional[str]:
        """Get the path to the Chromium executable."""
        if not self._webdriver_path:
            log_func("Webdriver path not set")
            return None

        chromium_dir = self._find_chromium_dir(self._webdriver_path, log_func)
        if not chromium_dir:
            return None

        chromium_path = os.path.join(chromium_dir, "chrome-win", "chrome.exe")
        if not os.path.exists(chromium_path):
            log_func(f"Chromium executable missing: {chromium_path}")
            return None

        return chromium_path
