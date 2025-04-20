"""
Session handler for managing browser sessions and interactions.
"""

import asyncio
import random
from typing import Any, Callable, Dict, List, Tuple

from app.models.account_model import AccountModel

from .browser_manager import BrowserManager

from patchright.async_api import async_playwright






class SessionHandler:
    """
    Handles browser sessions and interactions.
    Manages authentication, navigation, and actions.
    """


    def __init__(self):
        self.browser_manager = BrowserManager()

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
        chromium_exe = self.browser_manager.get_chromium_executable(log_func)
        if not chromium_exe:
            log_func(f"No chromium executable found for account {account_id}")
            return False

        user_data_dir = self.browser_manager.get_session_dir(account_id)
        log_func(
            f"Starting login for account {account_id} using session dir: {user_data_dir}"
        )

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch_persistent_context(
                    no_viewport=True,
                    channel="chrome",
                    headless=False,
                    user_data_dir=user_data_dir,
                )

                page = await browser.new_page()
                await page.goto("https://www.facebook.com/login")
                log_func(f"Navigated to Facebook login page for account {account_id}")

                # Wait for login form to appear
                email_field = await page.wait_for_selector("input#email", timeout=30000)
                password_field = await page.wait_for_selector(
                    "input#pass", timeout=30000
                )

                # Type the email with random delays between characters
                await self._type_with_human_delay(email_field, user, log_func)
                await asyncio.sleep(random.uniform(0.5, 2.0))
                await self._type_with_human_delay(password_field, password, log_func)

                # Click login button
                login_button = await page.wait_for_selector(
                    'button[name="login"]', timeout=30000
                )
                if login_button:
                    await login_button.click()
                else:
                    log_func(f"Login button not found for account {account_id}")
                    await page.screenshot(
                        path=f"{user_data_dir}/login_button_not_found.png"
                    )
                    await browser.close()
                    return False

                # Check if login was successful (wait for redirects)
                await asyncio.sleep(5)

                # Check if we're on the Facebook home page
                current_url = page.url
                login_successful = (
                    "login" not in current_url and "checkpoint" not in current_url
                )

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
                    cookies = await browser.cookies()
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
                if keep_browser_open_seconds > 0:
                    log_func(
                        f"Keeping browser open for {keep_browser_open_seconds} seconds for manual testing..."
                    )
                    await asyncio.sleep(keep_browser_open_seconds)

                await browser.close()
                return login_successful

        except Exception as e:
            log_func(f"Error during login for account {account_id}: {str(e)}")
            return False




    async def _type_with_human_delay(
        self, element, text: str, log_func: Callable[[str], None]
    ) -> None:
        
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
        Test multiple accounts, with configurable batch size and concurrency.
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
