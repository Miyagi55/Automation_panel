"""
Session handler for managing browser sessions and interactions.
"""

import asyncio
import random
from typing import Any, Callable, Dict, List, Tuple

from app.models.account_model import AccountModel
from app.utils.config import URL

from .browser_manager import BrowserManager


class SessionHandler:
    """
    Handles browser sessions and interactions.
    Manages authentication, navigation, and actions.
    """

    def __init__(self):
        self.browser_manager = BrowserManager()
<<<<<<< HEAD
        self._playwright = None  # shared Playwright instance
        self.url = URL

    async def _ensure_playwright(self):
        """
        Start a patchright Playwright instance if not already.
        """
        if self._playwright is None:
            from patchright.async_api import async_playwright

            self._playwright = await async_playwright().start()

    async def _shutdown_playwright(self):
        """
        Stop the Playwright instance.
        """
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
=======
>>>>>>> parent of f10fde1 (refactor: improve code formatting and readability in account_controller, session_handler, and account_view)

    # ---------- low‑level helpers ----------
    async def _open_context(
        self,
        account_id: str,
        log_func: Callable[[str], None],
        headless: bool = False,
    ):
        """
        Create or reuse a persistent Playwright context for the given account.
        Returns (browser_context, playwright_instance) so the caller can
        close them when appropriate.
        """
        chromium_exe = self.browser_manager.get_chromium_executable(log_func)
        if not chromium_exe:
            log_func(f"No chromium executable found for account {account_id}")
            return None, None

        user_data_dir = self.browser_manager.get_session_dir(account_id)
        # Ensure patchright is available
        try:
            from patchright.async_api import async_playwright
        except ImportError:
            log_func("Error: patchright library not found. Please install it.")
            return None, None

        p = await async_playwright().__aenter__()

        try:
            context = await p.chromium.launch_persistent_context(
                channel="chrome",
                headless=headless,
                no_viewport=True,
                user_data_dir=user_data_dir,
            )
            return context, p
        except Exception as e:
            log_func(f"Error launching browser context for {account_id}: {e}")
            await p.__aexit__(
                None, None, None
            )  # Clean up playwright instance if launch fails
            return None, None

    # ---------- high‑level operations ----------

    async def open_browser_context(
        self,
        account_id: str,
        log_func: Callable[[str], None],
        keep_open_seconds: int,
    ) -> bool:
        """
        Just open the browser (no login) and keep it open for the given time.
        Returns True if the context stayed alive the whole interval.
        """
        ctx, p = await self._open_context(account_id, log_func, headless=False)
        if not ctx:
            return False

        log_func(
            f"Opened browser for account {account_id}. "
            f"Keeping it open {keep_open_seconds}s…"
        )
        success = False
        try:
            # open URL
            page = await ctx.new_page()
            await page.goto(self.url)
            await asyncio.sleep(keep_open_seconds)
            success = True  # Assume success if sleep completes without error
        except asyncio.CancelledError:
            log_func(f"Browser opening cancelled for account {account_id}")
        except Exception as e:
            log_func(f"Error while keeping browser open for {account_id}: {e}")
        finally:
            try:
                await ctx.close()
            except Exception as e:
                log_func(f"Error closing browser context for {account_id}: {e}")
            try:
                # Use p.stop() to close the Playwright instance
                await p.stop()
            except Exception as e:
                log_func(f"Error closing Playwright instance for {account_id}: {e}")
            log_func(f"Closed browser for account {account_id}")
        return success

    async def login_account(
        self,
        account_id: str,
        user: str,
        password: str,
        log_func: Callable[[str], None],
        keep_browser_open_seconds: int = 0,
    ) -> bool:
        """
        Login to Facebook using account credentials.
        Returns True if login was successful, False otherwise.
        Optionally keeps the browser open for manual testing.
        """
        # Removed chromium_exe check and user_data_dir retrieval, handled by _open_context
        log_func(
            f"Starting login for account {account_id}"  # Simplified log message
        )

        ctx, p = await self._open_context(account_id, log_func, headless=False)
        if not ctx:
            return False # _open_context already logged the error

        login_successful = False # Initialize login status
        try:
            page = await ctx.new_page()
            await page.goto(URL + "/login")
            log_func(f"Navigated to Facebook login page for account {account_id}")

            # Wait for login form to appear
            email_field = await page.wait_for_selector("input#email", timeout=30000)
            password_field = await page.wait_for_selector("input#pass", timeout=30000)

            # Type the email with random delays between characters
            # Ensure log_func is not passed
            await self._type_with_human_delay(email_field, user)
            await asyncio.sleep(random.uniform(0.5, 2.0))
            # Ensure log_func is not passed
            await self._type_with_human_delay(password_field, password)

            # Click login button
            login_button = await page.wait_for_selector(
                'button[name="login"]', timeout=30000
            )
            if login_button:
                await login_button.click()
            else:
                log_func(f"Login button not found for account {account_id}")
                user_data_dir = self.browser_manager.get_session_dir(
                    account_id
                )  # Get dir for screenshot
                await page.screenshot(
                    path=f"{user_data_dir}/login_button_not_found.png"
                )
                # No return here, proceed to finally block for cleanup
                return False  # Explicitly return False

            # Check if login was successful (wait for redirects)
            await asyncio.sleep(
                5
            )  # Consider using page.wait_for_navigation() or similar

            # Check if we're on the Facebook home page
            current_url = page.url
            login_successful = (
                "login" not in current_url and "checkpoint" not in current_url
            )

            user_data_dir = self.browser_manager.get_session_dir(
                account_id
            )  # Get dir for screenshot
            if login_successful:
                log_func(f"Login successful for account {account_id}")
                # Take a screenshot as proof
                await page.screenshot(path=f"{user_data_dir}/login_success.png")
            else:
                log_func(f"Login failed for account {account_id}")
                # Take a screenshot to debug
                await page.screenshot(path=f"{user_data_dir}/login_failed.png")

            # --- Persist cookies after login attempt ---
            try:
                cookies = await ctx.cookies()  # Use context for cookies
                cookies_dicts = [dict(cookie) for cookie in cookies]

                account_model = AccountModel()
                account_model.update_account_cookies(account_id, cookies_dicts)
                log_func(f"Persisted cookies for account {account_id}")
            except Exception as e:
                log_func(
                    f"Failed to persist cookies for account {account_id}: {str(e)}"
                )
            # --- End persist cookies ---

            # If requested, keep the browser open for manual testing
            if (
                keep_browser_open_seconds > 0 and login_successful
            ):  # Only keep open on success?
                log_func(
                    f"Keeping browser open for {keep_browser_open_seconds} seconds for manual testing..."
                )
                await asyncio.sleep(keep_browser_open_seconds)
            # No explicit browser close here, handled in finally

        except Exception as e:
            log_func(f"Error during login for account {account_id}: {str(e)}")
            login_successful = False # Ensure failure on exception
        finally:
            # Ensure context and playwright instance are closed
            if ctx:
                try:
                    await ctx.close()
                except Exception as e:
                    log_func(f"Error closing browser context during login for {account_id}: {e}")
            if p:
                try:
                    # Use p.stop() to close the Playwright instance
                    await p.stop()
                except Exception as e:
                    log_func(f"Error closing Playwright instance during login for {account_id}: {e}")

        return login_successful

    async def _type_with_human_delay(self, element, text: str) -> None:
        """Type text with random delays between keystrokes to mimic human typing."""
        for char in text:
            await element.type(char, delay=0)
            await asyncio.sleep(random.uniform(0.05, 0.3))

    async def test_multiple_accounts(
        self,
        accounts: List[Dict[str, Any]],
        log_func: Callable[[str], None],
        batch_size: int = 3,
        concurrent_limit: int = 9,
    ) -> Dict[str, bool]:
        """
        Test multiple accounts concurrently, with configurable batch size and concurrency.
        """
        chromium_exe = self.browser_manager.get_chromium_executable(log_func)
        if not chromium_exe:
            log_func("No chromium executable available")
            return {account["account_id"]: False for account in accounts}

        # Limit concurrency
        semaphore = asyncio.Semaphore(concurrent_limit)
        results = {}

        async def test_account_with_semaphore(
            account: Dict[str, Any],
        ) -> Tuple[str, bool]:
            async with semaphore:
                log_func(f"Starting test for account {account['account_id']}")
                success = await self.login_account(
                    account["account_id"],
                    account["user"],
                    account["password"],
                    log_func,
                )
                return account["account_id"], success

        # Process accounts in batches
        for i in range(0, len(accounts), batch_size):
            batch = accounts[i : i + batch_size]
            log_func(
                f"Processing batch {i // batch_size + 1} with {len(batch)} accounts"
            )

            tasks = [test_account_with_semaphore(account) for account in batch]

            for completed_task in asyncio.as_completed(tasks):
                account_id, success = await completed_task
                results[account_id] = success
                log_func(
                    f"Completed test for account {account_id}: {'Success' if success else 'Failed'}"
                )

        return results
