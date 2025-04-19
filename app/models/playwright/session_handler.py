import asyncio
import random
from typing import Any, Callable, Dict, List, Tuple

from app.models.account_model import AccountModel
from app.utils.config import URL

from .browser_manager import BrowserManager


class SessionHandler:
    """
    Handles browser sessions and interactions using Playwright (via patchright).
    """

    def __init__(self):
        self.browser_manager = BrowserManager()
        self._playwright = None  # shared Playwright instance

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

    async def _open_context(
        self,
        account_id: str,
        log_func: Callable[[str], None],
        headless: bool = False,
    ) -> Tuple[Any, Any]:
        """
        Launch a persistent Chromium context for the account.
        Returns (context, playwright_instance) or (None, None) on failure.
        """
        await self._ensure_playwright()
        p = self._playwright

        chromium_exe = self.browser_manager.get_chromium_executable(log_func)
        if not chromium_exe:
            log_func(f"No chromium executable found for account {account_id}")
            return None, None

        user_data_dir = self.browser_manager.get_session_dir(account_id)
        try:
            context = await p.chromium.launch_persistent_context(
                executable_path=chromium_exe,
                headless=headless,
                no_viewport=True,
                user_data_dir=user_data_dir,
                args=[],  # override default flags, removes --no-sandbox
            )
            return context, p
        except Exception as e:
            log_func(f"Error launching browser context for {account_id}: {e}")
            return None, None

    async def open_browser_context(
        self,
        account_id: str,
        log_func: Callable[[str], None],
        keep_open_seconds: int,
    ) -> bool:
        """
        Open browser context without login and keep it open for the interval.
        """
        ctx, p = await self._open_context(account_id, log_func, headless=False)
        if not ctx:
            return False

        log_func(
            f"Opened browser for account {account_id}, keeping it open {keep_open_seconds}s…"
        )
        success = False
        try:
            await asyncio.sleep(keep_open_seconds)
            success = True
        except Exception as e:
            log_func(f"Error during open_browser_context for {account_id}: {e}")
        finally:
            try:
                await ctx.close()
            except Exception as e:
                log_func(f"Error closing context for {account_id}: {e}")
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
        Log in to Facebook and optionally keep browser open on success.
        """
        log_func(f"Starting login for account {account_id}")
        ctx, p = await self._open_context(account_id, log_func, headless=False)
        if not ctx:
            return False

        login_successful = False
        try:
            page = await ctx.new_page()
            await page.goto(URL + "/login")
            log_func(f"Navigated to login page for {account_id}")

            email_field = await page.wait_for_selector("input#email", timeout=30000)
            pwd_field = await page.wait_for_selector("input#pass", timeout=30000)

            await self._type_with_human_delay(email_field, user)
            await asyncio.sleep(random.uniform(0.5, 2.0))
            await self._type_with_human_delay(pwd_field, password)

            btn = await page.wait_for_selector('button[name="login"]', timeout=30000)
            if not btn:
                log_func(f"Login button missing for {account_id}")
                await page.screenshot(
                    path=f"{user_data_dir}/login_button_not_found.png"
                )
                return False
            await btn.click()

            await asyncio.sleep(5)
            current_url = page.url
            login_successful = (
                "login" not in current_url and "checkpoint" not in current_url
            )

            user_data_dir = self.browser_manager.get_session_dir(account_id)
            screenshot = "login_success.png" if login_successful else "login_failed.png"
            log_func(
                f"Login {'succeeded' if login_successful else 'failed'} for {account_id}"
            )
            await page.screenshot(path=f"{user_data_dir}/{screenshot}")

            # Persist cookies
            try:
                cookies = await ctx.cookies()
                AccountModel().update_account_cookies(
                    account_id, [dict(c) for c in cookies]
                )
                log_func(f"Persisted cookies for {account_id}")
            except Exception as e:
                log_func(f"Cookie save error for {account_id}: {e}")

            if keep_browser_open_seconds and login_successful:
                log_func(
                    f"Keeping browser open for {keep_browser_open_seconds}s for testing…"
                )
                await asyncio.sleep(keep_browser_open_seconds)

        except Exception as e:
            log_func(f"Error during login for {account_id}: {e}")
        finally:
            try:
                await ctx.close()
            except:
                pass
        return login_successful

    async def _type_with_human_delay(self, element, text: str) -> None:
        """
        Type text character-by-character with slight random delays.
        """
        for ch in text:
            await element.type(ch)
            await asyncio.sleep(random.uniform(0.05, 0.3))

    async def test_multiple_accounts(
        self,
        accounts: List[Dict[str, Any]],
        log_func: Callable[[str], None],
        batch_size: int = 3,
        concurrent_limit: int = 9,
    ) -> Dict[str, bool]:
        """
        Concurrently test multiple account logins in batches.
        """
        semaphore = asyncio.Semaphore(concurrent_limit)
        results = {}

        async def _test(acc: Dict[str, Any]) -> Tuple[str, bool]:
            async with semaphore:
                log_func(f"Testing {acc['account_id']}")
                ok = await self.login_account(
                    acc["account_id"], acc["user"], acc["password"], log_func
                )
                return acc["account_id"], ok

        for i in range(0, len(accounts), batch_size):
            batch = accounts[i : i + batch_size]
            log_func(f"Batch {i//batch_size+1}: testing {len(batch)} accounts")
            tasks = [asyncio.create_task(_test(acc)) for acc in batch]
            for coro in asyncio.as_completed(tasks):
                acc_id, ok = await coro
                results[acc_id] = ok
                log_func(f"{acc_id} test {'passed' if ok else 'failed'}")

        # Shutdown Playwright if needed
        if self._playwright:
            await self._shutdown_playwright()

        return results
