import asyncio
from typing import Any, Callable, Optional, Tuple

from ..browser_manager import BrowserManager


class BrowserUtils:
    """Utility class for browser-related operations."""

    def __init__(self, account_id: str, log_func: Callable[[str], None]):
        self.account_id = account_id
        self.log_func = log_func
        self.browser_manager = BrowserManager()

    def get_session_dir(self) -> str:
        """Get the session directory for the account."""
        return self.browser_manager.get_session_dir(self.account_id)

    async def initialize_browser(
        self, browser: Optional[Any], user_data_dir: str
    ) -> Tuple[bool, Optional[Any], Any]:
        """Initialize or reuse a browser context."""
        created_browser = False
        playwright = None
        from patchright.async_api import async_playwright

        try:
            if browser and not (hasattr(browser, '_closed') and browser._closed):
                self.log_func(f"Reusing browser context for account {self.account_id}")
            else:
                if not self.browser_manager.get_chromium_executable(self.log_func):
                    raise RuntimeError(f"No chromium executable found for account {self.account_id}")
                playwright = await async_playwright().__aenter__()
                browser = await playwright.chromium.launch_persistent_context(
                    no_viewport=True,
                    channel="chrome",
                    headless=False,
                    user_data_dir=user_data_dir,
                )
                created_browser = True
                self.log_func(f"Created browser context for account {self.account_id}")
            return created_browser, playwright, browser
        except Exception as e:
            self.log_func(f"Failed to initialize browser for account {self.account_id}: {str(e)}")
            raise

    async def cleanup_browser(
        self, created_browser: bool, browser: Optional[Any], playwright: Optional[Any]
    ) -> None:
        """Clean up browser and Playwright resources."""
        try:
            if created_browser and browser and not (hasattr(browser, '_closed') and browser._closed):
                await browser.close()
                self.log_func(f"Ensured browser closed for account {self.account_id}")
            if playwright:
                await playwright.__aexit__(None, None, None)
                self.log_func(f"Closed Playwright instance for account {self.account_id}")
        except Exception as e:
            self.log_func(f"Error during browser cleanup for account {self.account_id}: {str(e)}")

    async def scroll_element(self, element: Any, name: str, distance: int, debug: bool) -> None:
        """Attempt to scroll an element by a specified distance."""
        try:
            scroll_before = await element.evaluate("() => window.scrollY" if name == "Page" else "el => el.scrollTop")
            await element.evaluate(f"{'window' if name == 'Page' else 'el'}.scrollBy(0, {distance})")
            scroll_after = await element.evaluate("() => window.scrollY" if name == "Page" else "el => el.scrollTop")
            if debug:
                self.log_func(f"{name} scroll: {scroll_before} -> {scroll_after}")
            if scroll_after <= scroll_before and debug:
                self.log_func(f"No scrollable element responded for account {self.account_id}")
        except Exception as e:
            if debug:
                self.log_func(f"Failed to scroll {name}: {str(e)}")