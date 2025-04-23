from typing import Any, Callable, Optional
from patchright.async_api import async_playwright
from .browser_manager import BrowserManager


class BrowserContext:
    """Manages browser context creation and configuration."""

    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager

    async def create_browser_context(self, account_id: str, log_func: Callable[[str], None]) -> Optional[Any]:
        """Creates a persistent browser context for the given account."""
        chromium_exe = self.browser_manager.get_chromium_executable(log_func)
        if not chromium_exe:
            log_func(f"No chromium executable found for account {account_id}")
            return None

        user_data_dir = self.browser_manager.get_session_dir(account_id)
        log_func(f"Starting browser for account {account_id} using session dir: {user_data_dir}")

        try:
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch_persistent_context(
                no_viewport=True,
                channel="chrome",
                headless=False,
                user_data_dir=user_data_dir,
            )
            # Store playwright instance in browser for later cleanup
            browser._playwright_instance = playwright
            return browser
        except Exception as e:
            log_func(f"Error creating browser context for account {account_id}: {str(e)}")
            return None