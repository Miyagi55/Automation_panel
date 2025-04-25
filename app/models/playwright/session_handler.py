import asyncio
import random
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Tuple, Optional

from .browser_context import BrowserContext
from .login_handler import LoginHandler
from .cookie_manager import CookieManager
from .batch_processor import BatchProcessor
from .browser_manager import BrowserManager


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
    ) -> Tuple[bool, bool, Optional[Any], Optional[Any]]:
        """
        Login to Facebook using account credentials, followed by feed simulation.
        Returns (login_successful, sim_success, browser, playwright_instance).
        """
        user_data_dir = self.browser_manager.get_session_dir(account_id)
        browser = await self.browser_context.create_browser_context(account_id, log_func)
        playwright_instance = browser._playwright_instance if browser else None
        if not browser:
            log_func(f"Failed to create browser context for account {account_id}")
            return False, False, None, None

        try:
            login_successful = await self.login_handler.perform_login(
                browser, account_id, user, password, log_func, user_data_dir, captcha_timeout=60
            )

            # Persist cookies
            await self.cookie_manager.save_cookies(browser, account_id, log_func)

            # Run feed simulation if login is successful
            sim_success = False
            if login_successful:
                sim_success = await self.simulate_facebook_feed(
                    account_id, "https://www.facebook.com", browser, log_func, max_execution_time=60
                )
                if not sim_success:
                    log_func(f"Feed simulation failed for account {account_id}, keeping browser open for 60 seconds")
                    await asyncio.sleep(60)
            else:
                log_func(f"Skipping feed simulation for account {account_id} due to login failure")
                log_func(f"Keeping browser open for 60 seconds for manual inspection for account {account_id}")
                await asyncio.sleep(60)

            # Keep browser open if requested
            if keep_browser_open_seconds > 0:
                log_func(f"Keeping browser open for {keep_browser_open_seconds} seconds for manual testing...")
                await asyncio.sleep(keep_browser_open_seconds)

            return login_successful, sim_success, browser, playwright_instance
        finally:
            if browser and not (hasattr(browser, '_closed') and browser._closed):
                try:
                    await browser.close()
                    log_func(f"Closed browser for account {account_id}")
                except Exception as e:
                    log_func(f"Error closing browser for account {account_id}: {str(e)}")
                if playwright_instance:
                    try:
                        await playwright_instance.stop()
                        log_func(f"Stopped Playwright instance for account {account_id}")
                    except Exception as e:
                        log_func(f"Error stopping Playwright instance for account {account_id}: {str(e)}")

    async def auto_login_accounts(
        self,
        accounts: List[Dict[str, Any]],
        log_func: Callable[[str], None],
        batch_size: int = 3,
        concurrent_limit: int = 9,
    ) -> Dict[str, Tuple[bool, bool]]:
        """
        Test multiple accounts, with configurable batch size and concurrency.
        """
        return await self.batch_processor.auto_login_accounts(accounts, log_func, batch_size, concurrent_limit)

    async def open_sessions(
        self,
        account_ids: str | List[str],
        log_func: Callable[[str], None],
        keep_browser_open_seconds: int,
        skip_simulation: bool = False,
    ) -> Dict[str, Tuple[bool, bool]]:
        """
        Open sessions for one or multiple accounts concurrently using batch processing,
        followed by feed simulation for logged-in sessions.
        Returns (is_logged_in, sim_success).
        Browser contexts and Playwright instances are stored in BatchProcessor.
        """
        # Normalize input to a list
        if isinstance(account_ids, str):
            account_ids = [account_ids]

        async def open_session_task(account_id: str, log_func: Callable[[str], None], keep_browser_open_seconds: int) -> Tuple[bool, bool, Optional[Any], Optional[Any]]:
            log_func(f"Attempting to open session for account {account_id}")
            user_data_dir = self.browser_manager.get_session_dir(account_id)
            home_url = "https://www.facebook.com"

            # Check if session directory exists
            if not user_data_dir:
                log_func(f"No session directory found for account {account_id} at {user_data_dir}")
                return False, False, None, None

            # Create browser context without context manager
            from patchright.async_api import async_playwright
            p = await async_playwright().start()
            try:
                browser = await p.chromium.launch_persistent_context(
                    no_viewport=True,
                    channel="chrome",
                    headless=False,
                    user_data_dir=user_data_dir,
                )
                try:
                    # Save cookies
                    await self.cookie_manager.save_cookies(browser, account_id, log_func)

                    # Open a new page and navigate to Facebook home URL with retries
                    page = await browser.new_page()
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            await page.goto(home_url, wait_until="domcontentloaded", timeout=60000)
                            log_func(f"Navigated to {home_url} for account {account_id}")
                            break
                        except Exception as e:
                            log_func(f"Navigation failed for account {account_id} (attempt {attempt + 1}): {str(e)}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2.0)
                            else:
                                log_func(f"Failed to navigate to {home_url} for account {account_id} after {max_retries} attempts")
                                return False, False, None, None

                    # Verify login state
                    login_form = await page.query_selector("input#email")
                    is_logged_in = login_form is None
                    sim_success = False

                    if is_logged_in:
                        log_func(f"Account {account_id} is logged in")
                        # Wait for "What's on your mind" text to confirm logged-in state with feed
                        try:
                            await page.wait_for_selector(
                                '//div[contains(text(), "What\'s on your mind")]', timeout=10000
                            )
                            log_func(f"'What's on your mind' text found for account {account_id}, indicating feed presence")
                            if not skip_simulation:
                                sim_success = await self.simulate_facebook_feed(
                                    account_id, home_url, browser, log_func, max_execution_time=60, page=page
                                )
                            else:
                                sim_success = True  # Assume success if simulation is skipped
                        except Exception as e:
                            log_func(f"Failed to find 'What's on your mind' text for account {account_id}: {str(e)}")
                            sim_success = False
                    else:
                        log_func(f"Account {account_id} is not logged in: Login form detected")

                    # Keep browser open if requested
                    if keep_browser_open_seconds > 0:
                        log_func(f"Keeping browser open for {keep_browser_open_seconds} seconds for account {account_id}")
                        await asyncio.sleep(keep_browser_open_seconds)

                    return is_logged_in, sim_success, browser, p

                except Exception as e:
                    log_func(f"Error opening session for account {account_id}: {str(e)}")
                    if browser and not (hasattr(browser, '_closed') and browser._closed):
                        await browser.close()
                    return False, False, None, None
            except Exception as e:
                log_func(f"Error starting Playwright for account {account_id}: {str(e)}")
                await p.stop()
                return False, False, None, None

        results = await self.batch_processor.process_batch(
            items=account_ids,
            process_func=open_session_task,
            log_func=log_func,
            batch_size=3,
            concurrent_limit=9,
            keep_browser_open_seconds=keep_browser_open_seconds
        )
        return results

    async def simulate_facebook_feed(
        self,
        account_id: str,
        url: str,
        browser: Any,
        log_func: Callable[[str], None],
        max_execution_time: int = 60,
        page: Any = None
    ) -> bool:
        log_func(f"Starting feed simulation for account {account_id} at {url}")
        try:
            # Use existing page if provided, otherwise create a new one
            if page is None:
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                log_func(f"Navigated to {url} for account {account_id}")

            # Verify login state
            login_form = await page.query_selector("input#email")
            if login_form:
                log_func(f"Account {account_id} is not logged in: Login form detected")
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

                # Randomly stop and do nothing (20% chance, 2-7 seconds)
                if random.random() < 0.2:
                    await asyncio.sleep(random.uniform(2, 7))

            log_func(f"Feed simulation completed successfully for account {account_id}")
            return True
        except Exception as e:
            log_func(f"Error during feed simulation for account {account_id}: {str(e)}")
            return False
        finally:
            if page and not (hasattr(page, '_closed') and page._closed):
                try:
                    log_func(f"Simulation steps ended for account: {account_id}")
                except Exception as e:
                    log_func(f"Error closing page for account {account_id}: {str(e)}")