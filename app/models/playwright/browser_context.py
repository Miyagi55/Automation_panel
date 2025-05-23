from typing import Any, Callable, Optional

from patchright.async_api import async_playwright

from .browser_manager import BrowserManager


class BrowserContext:
    """Manages browser context creation and configuration."""

    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager

    async def create_browser_context(
        self, account_id: str, log_func: Callable[[str], None], settings_controller=None
    ) -> Optional[Any]:
        """Creates a persistent browser context for the given account."""
        chromium_exe = self.browser_manager.get_chromium_executable(log_func)
        if not chromium_exe:
            log_func(f"No chromium executable found for account {account_id}")
            return None

        user_data_dir = self.browser_manager.get_session_dir(account_id)
        log_func(
            f"Starting browser for account {account_id} using session dir: {user_data_dir}"
        )

        # Check cache setting and prepare args
        cache_enabled = True
        if settings_controller:
            cache_enabled = settings_controller.get_setting("cache_enabled")

        # Prepare browser args
        browser_args = []
        if not cache_enabled:
            # Add cache-disabling arguments
            browser_args.extend(
                [
                    "--disable-application-cache",
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                    "--disable-backgrounding-occluded-windows",
                    "--aggressive-cache-discard",
                    "--disable-features=TranslateUI",
                    "--disable-ipc-flooding-protection",
                    "--memory-pressure-off",
                    "--max_old_space_size=4096",
                ]
            )
            log_func(
                f"Cache disabled for account {account_id} - browser will run without disk cache"
            )

        try:
            playwright = await async_playwright().start()

            # Configure browser launch options
            launch_options = {
                "no_viewport": True,
                "channel": "chrome",
                "headless": False,
                "user_data_dir": user_data_dir,
            }

            # Add args if cache is disabled
            if browser_args:
                launch_options["args"] = browser_args

            browser = await playwright.chromium.launch_persistent_context(
                **launch_options
            )

            # Store playwright instance in browser for later cleanup
            browser._playwright_instance = playwright
            return browser
        except Exception as e:
            log_func(
                f"Error creating browser context for account {account_id}: {str(e)}"
            )
            return None
