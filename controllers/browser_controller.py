"""
Browser controller to manage Playwright browser functionality.
"""

import threading
from typing import Callable, Optional

from models.playwright.browser_manager import BrowserManager
from utils.logger import logger


class BrowserController:
    """
    Controller for browser operations.
    Manages browser installation and configuration.
    """

    def __init__(self):
        """Initialize the browser controller."""
        self.browser_manager = BrowserManager()

    def get_webdriver_path(self) -> Optional[str]:
        """Get the current webdriver path."""
        return self.browser_manager.webdriver_path

    def install_webdrivers(self, update_progress: Callable[[str, float], None]) -> None:
        """
        Install Playwright webdrivers.

        Args:
            update_progress: Callback for progress updates
        """

        def install_thread():
            """Run installation in a separate thread."""
            success = self.browser_manager.install_webdrivers(
                logger.info, update_progress
            )
            if success:
                logger.info("Webdrivers installed successfully")
            else:
                logger.error("Failed to install webdrivers")

        # Start installation in a thread to keep UI responsive
        install_thread = threading.Thread(target=install_thread)
        install_thread.daemon = True
        install_thread.start()

    def get_chromium_executable(self) -> Optional[str]:
        """Get the path to the Chromium executable."""
        return self.browser_manager.get_chromium_executable(logger.info)

    def verify_installation(self) -> bool:
        """Verify the webdriver installation."""
        return self.browser_manager.webdriver_path is not None

    def get_session_dir(self, account_id: str) -> str:
        """
        Get the session directory for a given account ID.

        Args:
            account_id: The account ID

        Returns:
            Path to the session directory
        """
        return self.browser_manager.get_session_dir(account_id)
