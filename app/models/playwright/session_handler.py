"""
Session handler for managing browser sessions and interactions.
"""

import asyncio
import random
from typing import Any, Callable, Dict, List, Tuple

from app.models.account_model import AccountModel
from .browser_manager import BrowserManager
from app.utils.config import LINK_LOGIN
from patchright.async_api import async_playwright




#----------------------------------------class-------------------------------------------!!!!!!!
class BrowserContext:
    """Manages browser context creation and configuration."""

    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager

    async def create_browser_context(self, account_id: str, log_func: Callable[[str], None]):
        """Creates a persistent browser context for the given account."""
        chromium_exe = self.browser_manager.get_chromium_executable(log_func)
        if not chromium_exe:
            log_func(f"No chromium executable found for account {account_id}")
            return None

        user_data_dir = self.browser_manager.get_session_dir(account_id)
        log_func(f"Starting browser for account {account_id} using session dir: {user_data_dir}")

        try:
            playwright = await async_playwright().__aenter__()
            browser = await playwright.chromium.launch_persistent_context(
                no_viewport=True,
                channel="chrome",
                headless=False,
                user_data_dir=user_data_dir,
            )
            return browser
        except Exception as e:
            log_func(f"Error creating browser context for account {account_id}: {str(e)}")
            return None





#----------------------------------------class-------------------------------------------!!!!!!!
class LoginHandler:
    """Handles the login process for a single account."""

    async def perform_login(
        self,
        browser,
        account_id: str,
        user: str,
        password: str,
        log_func: Callable[[str], None],
        user_data_dir: str,
    ) -> bool:
        """Executes the login process and returns True if successful."""
        try:
            page = await browser.new_page()
            await page.goto(LINK_LOGIN)
            log_func(f"Navigated to login page for account {account_id}")

            # Wait for login form
            email_field = await page.wait_for_selector("input#email", timeout=30000)
            password_field = await page.wait_for_selector("input#pass", timeout=30000)

            # Type credentials with human-like delay
            await self._type_with_human_delay(email_field, user, log_func)
            await asyncio.sleep(random.uniform(0.5, 2.0))
            await self._type_with_human_delay(password_field, password, log_func)

            # Click login button
            login_button = await page.wait_for_selector('button[name="login"]', timeout=30000)
            if login_button:
                await login_button.click()
            else:
                log_func(f"Login button not found for account {account_id}")
                await page.screenshot(path=f"{user_data_dir}/login_button_not_found.png")
                return False

            # Wait for navigation and check success
            await asyncio.sleep(5)
            current_url = page.url
            login_successful = "login" not in current_url and "checkpoint" not in current_url

            # Save screenshot for debugging
            screenshot_path = (
                f"{user_data_dir}/login_success.png" if login_successful else f"{user_data_dir}/login_failed.png"
            )
            await page.screenshot(path=screenshot_path)
            log_func(f"Login {'successful' if login_successful else 'failed'} for account {account_id}")

            return login_successful
        except Exception as e:
            log_func(f"Error during login for account {account_id}: {str(e)}")
            return False

    async def _type_with_human_delay(self, element, text: str, log_func: Callable[[str], None]) -> None:
        """Simulates human-like typing with random delays."""
        for char in text:
            await element.type(char, delay=0)
            await asyncio.sleep(random.uniform(0.05, 0.3))




#----------------------------------------class-------------------------------------------!!!!!!!
class CookieManager:
    """Manages cookie persistence for accounts."""

    async def save_cookies(self, browser, account_id: str, log_func: Callable[[str], None]) -> None:
        """Persists cookies for the given account."""
        try:
            cookies = await browser.cookies()
            cookies_dicts = [dict(cookie) for cookie in cookies]

            account_model = AccountModel()
            account_model.update_account_cookies(account_id, cookies_dicts)
            log_func(f"Persisted cookies for account {account_id}")

        except Exception as e:
            log_func(f"Failed to persist cookies for account {account_id}: {str(e)}")





#----------------------------------------class-------------------------------------------!!!!!!!
class BatchProcessor:
    """Handles batch processing of multiple accounts with concurrency control."""

    def __init__(self, session_handler):
        self.session_handler = session_handler

    async def auto_login_accounts(
        self,
        accounts: List[Dict[str, Any]],
        log_func: Callable[[str], None],
        batch_size: int = 3,
        concurrent_limit: int = 9,
    ) -> Dict[str, bool]:
        """Tests multiple accounts with batching and concurrency limits."""
        browser_manager = self.session_handler.browser_manager
        if not browser_manager.get_chromium_executable(log_func):
            log_func("No chromium executable available")
            return {account["account_id"]: False for account in accounts}

        semaphore = asyncio.Semaphore(concurrent_limit)
        results = {}

        async def test_account_with_semaphore(account: Dict[str, Any]) -> Tuple[str, bool]:
            async with semaphore:
                log_func(f"Starting test for account {account['account_id']}")
                success = await self.session_handler.login_account(
                    account["account_id"],
                    account["user"],
                    account["password"],
                    log_func,
                )
                return account["account_id"], success

        # Process accounts in batches
        for i in range(0, len(accounts), batch_size):
            batch = accounts[i : i + batch_size]
            log_func(f"Processing batch {i // batch_size + 1} with {len(batch)} accounts")

            tasks = [test_account_with_semaphore(account) for account in batch]
            for completed_task in asyncio.as_completed(tasks):
                account_id, success = await completed_task
                results[account_id] = success
                log_func(
                    f"Completed test for account {account_id}: {'Success' if success else 'Failed'}"
                )

        return results





#----------------------------------------class-------------------------------------------!!!!!!!
class SessionHandler:
    """
    Coordinates browser sessions and interactions.
    Delegates tasks to specialized classes for login, cookies, and batch processing.
    """

    def __init__(self):
        self.browser_manager = BrowserManager()
        self.browser_context = BrowserContext(self.browser_manager)
        self.login_handler = LoginHandler()
        self.cookie_manager = CookieManager()
        self.batch_processor = BatchProcessor(self)

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
        user_data_dir = self.browser_manager.get_session_dir(account_id)
        browser = await self.browser_context.create_browser_context(account_id, log_func)
        if not browser:
            return False

        try:
            login_successful = await self.login_handler.perform_login(
                browser, account_id, user, password, log_func, user_data_dir
            )

            # Persist cookies
            await self.cookie_manager.save_cookies(browser, account_id, log_func)

            # Keep browser open if requested
            if keep_browser_open_seconds > 0:
                log_func(f"Keeping browser open for {keep_browser_open_seconds} seconds for manual testing...")
                await asyncio.sleep(keep_browser_open_seconds)

            return login_successful
        finally:
            await browser.close()

    async def auto_login_accounts(
        self,
        accounts: List[Dict[str, Any]],
        log_func: Callable[[str], None],
        batch_size: int = 3,
        concurrent_limit: int = 9,
    ) -> Dict[str, bool]:
        """
        Test multiple accounts, with configurable batch size and concurrency.
        """
        return await self.batch_processor.auto_login_accounts(accounts, log_func, batch_size, concurrent_limit)
    


    async def open_sessions(
        self,
        account_ids: str | List[str],
        log_func: Callable[[str], None],
        keep_browser_open_seconds: int,
    ) -> Dict[str, bool]: 

        # Normalize input to a list
        if isinstance(account_ids, str):
            account_ids = [account_ids]
        
        results = {}
        home_url = "https://www.facebook.com/home"

        for account_id in account_ids:
            log_func(f"Attempting to open session for account {account_id}")
            user_data_dir = self.browser_manager.get_session_dir(account_id)

            
            # Check if session directory exists
            if not self.browser_manager.get_session_dir(account_id):
                log_func(f"No session directory found for account {account_id} at {user_data_dir}")
                results[account_id] = False
                continue

            # Create browser context
            browser = await self.browser_context.create_browser_context(account_id, log_func)
            await self.cookie_manager.save_cookies(browser, account_id, log_func)
            if not browser:
                log_func(f"Failed to create browser context for account {account_id}")
                results[account_id] = False
                continue

            try:
        
                # Open a new page and navigate to Facebook home URL
                page = await browser.new_page()
                await page.goto(home_url)
                log_func(f"Navigated to {home_url} for account {account_id}")

                # Verify navigation success (basic check: page loaded and URL is correct)
                current_url = page.url
                navigation_successful = home_url in current_url and "login" not in current_url
                if navigation_successful:
                    log_func(f"Successfully opened session for account {account_id}")
                else:
                    log_func(f"Failed to verify navigation for account {account_id}. Current URL: {current_url}")
                    

                # Keep browser open if requested
                if keep_browser_open_seconds > 0:
                    log_func(f"Keeping browser open for {keep_browser_open_seconds} seconds for account {account_id}")
                    await asyncio.sleep(keep_browser_open_seconds)

                results[account_id] = navigation_successful

            except Exception as e:
                log_func(f"Error opening session for account {account_id}: {str(e)}")
                results[account_id] = False
            finally:
                await browser.close()
                log_func(f"Closed browser for account {account_id}")

        return results
