"""
Session handler for managing browser sessions and interactions.
"""

import asyncio
import random
from datetime import datetime, timedelta
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
                return False

            # Wait for navigation and check success
            await asyncio.sleep(5)
            current_url = page.url
            login_successful = "login" not in current_url and "checkpoint" not in current_url

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


    async def process_batch(
        self,
        items: List[Any],
        process_func: Callable,
        log_func: Callable[[str], None],
        batch_size: int = 3,
        concurrent_limit: int = 9,
        **kwargs
    ) -> Dict[Any, bool]:
        """
        Generic method to process items in batches with concurrency control.
        Takes a processing function and additional keyword arguments for the function.
        """
        if not items:
            log_func("No items to process")
            return {}

        semaphore = asyncio.Semaphore(concurrent_limit)
        results = {}


        async def process_item_with_semaphore(item: Any) -> Tuple[Any, bool]:
            async with semaphore:
                log_func(f"Starting processing for item {item}")
                try:
                    # Pass item and kwargs to the processing function
                    success = await process_func(item, log_func=log_func, **kwargs)
                    return item, success
                except Exception as e:
                    log_func(f"Error processing item {item}: {str(e)}")
                    return item, False

        # Process items in batches
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            log_func(f"Processing batch {i // batch_size + 1} with {len(batch)} items")

            tasks = [process_item_with_semaphore(item) for item in batch]
            for completed_task in asyncio.as_completed(tasks):
                item, success = await completed_task
                results[item] = success
                log_func(
                    f"Completed processing for item {item}: {'Success' if success else 'Failed'}"
                )

        return results


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


        async def login_task(account: Dict[str, Any], log_func: Callable[[str], None]) -> bool:
            return await self.session_handler.login_account(
                account["account_id"],
                account["user"],
                account["password"],
                log_func,
            )

        return await self.process_batch(
            items=accounts,
            process_func=login_task,
            log_func=log_func,
            batch_size=batch_size,
            concurrent_limit=concurrent_limit
        )





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
        Login to Facebook using account credentials, followed by feed simulation.
        Returns True if both login and simulation are successful, False otherwise.
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

            # Run feed simulation if login is successful
            sim_success = False
            if login_successful:
                sim_success = await self.simulate_facebook_feed(
                    account_id, "https://www.facebook.com", browser, log_func, max_execution_time=60
                )
            else:
                log_func(f"Skipping feed simulation for account {account_id} due to login failure")

            # Keep browser open if requested
            if keep_browser_open_seconds > 0:
                log_func(f"Keeping browser open for {keep_browser_open_seconds} seconds for manual testing...")
                await asyncio.sleep(keep_browser_open_seconds)

            return login_successful and sim_success
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
        """
        Open sessions for one or multiple accounts concurrently using batch processing,
        followed by feed simulation.
        """
        # Normalize input to a list
        if isinstance(account_ids, str):
            account_ids = [account_ids]
        
        async def open_session_task(account_id: str, log_func: Callable[[str], None], keep_browser_open_seconds: int) -> bool:
            log_func(f"Attempting to open session for account {account_id}")
            user_data_dir = self.browser_manager.get_session_dir(account_id)
            home_url = "https://www.facebook.com"

            # Check if session directory exists
            if not user_data_dir:
                log_func(f"No session directory found for account {account_id} at {user_data_dir}")
                return False

            # Create browser context
            browser = await self.browser_context.create_browser_context(account_id, log_func)
            if not browser:
                log_func(f"Failed to create browser context for account {account_id}")
                return False

            try:
                # Save cookies
                await self.cookie_manager.save_cookies(browser, account_id, log_func)

                # Open a new page and navigate to Facebook home URL
                page = await browser.new_page()
                await page.goto(home_url, wait_until="domcontentloaded", timeout=60000)
                log_func(f"Navigated to {home_url} for account {account_id}")

                # Verify navigation success and login state
                current_url = page.url
                navigation_successful = home_url in current_url and "login" not in current_url and "checkpoint" not in current_url
                if navigation_successful:
                    log_func(f"Successfully opened session for account {account_id}")
                else:
                    log_func(f"Failed to verify navigation for account {account_id}. Current URL: {current_url}")
                    return False

                # Run feed simulation
                sim_success = await self.simulate_facebook_feed(
                    account_id, home_url, browser, log_func, max_execution_time=60
                )

                # Keep browser open if requested
                if keep_browser_open_seconds > 0:
                    log_func(f"Keeping browser open for {keep_browser_open_seconds} seconds for account {account_id}")
                    await asyncio.sleep(keep_browser_open_seconds)

                return navigation_successful and sim_success

            except Exception as e:
                log_func(f"Error opening session for account {account_id}: {str(e)}")
                return False
            finally:
                await browser.close()
                log_func(f"Closed browser for account {account_id}")

        return await self.batch_processor.process_batch(
            items=account_ids,
            process_func=open_session_task,
            log_func=log_func,
            batch_size=3,
            concurrent_limit=9,
            keep_browser_open_seconds=keep_browser_open_seconds
        )




    async def simulate_facebook_feed(
        self,
        account_id: str,
        url: str,
        browser: Any,
        log_func: Callable[[str], None],
        max_execution_time: int = 60
    ) -> bool:
        """
        Simulates user interaction on the Facebook feed for a given account using an existing browser context.
        Returns True if simulation completes successfully, False otherwise.
        """
        log_func(f"Starting feed simulation for account {account_id} at {url}")
        try:
            page = await browser.new_page()
            for attempt in range(3):  # Retry up to 3 times
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    log_func(f"Navigated to {url} for account {account_id}")
                    break
                except Exception as e:
                    log_func(f"Navigation attempt {attempt + 1} failed for account {account_id}: {str(e)}")
                    if attempt == 2:
                        raise e
                    await asyncio.sleep(2)

            # Verify login state
            current_url = page.url
            if "login" in current_url or "checkpoint" in current_url:
                log_func(f"Account {account_id} is not logged in. Current URL: {current_url}")
                return False

            # Calculate end time
            start_time = datetime.now()
            end_time = start_time + timedelta(seconds=max_execution_time)

            while datetime.now() < end_time:
                # Random scroll distance (between 300 and 1000 pixels)
                scroll_distance = random.randint(300, 1000)
                await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                log_func(f"Scrolled {scroll_distance} pixels for account {account_id}")

                # Random pause (between 1 and 5 seconds)
                await asyncio.sleep(random.uniform(1, 5))

                # Occasionally click a post (30% chance)
                if random.random() < 0.3:
                    posts = await page.query_selector_all('a[href*="/posts/"]')
                    if posts:
                        post = random.choice(posts)
                        await post.click()
                        log_func(f"Clicked a post for account {account_id}")
                        await asyncio.sleep(random.uniform(2, 6))
                        await page.go_back()
                        log_func(f"Returned to feed for account {account_id}")
                        await asyncio.sleep(random.uniform(1, 3))

                # Randomly stop and do nothing (20% chance, 2-7 seconds)
                if random.random() < 0.2:
                    await asyncio.sleep(random.uniform(2, 7))

            log_func(f"Feed simulation completed successfully for account {account_id}")
            return True
        except Exception as e:
            log_func(f"Error during feed simulation for account {account_id}: {str(e)}")
            return False