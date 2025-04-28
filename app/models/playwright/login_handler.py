import asyncio
import random
from typing import Callable, Any


class LoginHandler:
    """Handles the login process for a single account."""

    async def perform_login(
        self,
        browser: Any,
        account_id: str,
        user: str,
        password: str,
        log_func: Callable[[str], None],
        user_data_dir: str,
    ) -> bool:
        """Executes the login process and returns True if successful."""
        try:
            page = await browser.new_page()
            from app.utils.config import LINK_LOGIN
            await page.goto(LINK_LOGIN, wait_until="domcontentloaded", timeout=60000)
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

            # Wait for navigation and check login state
            await asyncio.sleep(5)
            login_form = await page.query_selector("input#email")
            login_successful = login_form is None

            log_func(f"Login {'successful' if login_successful else 'failed'} for account {account_id}")

            return login_successful
        except Exception as e:
            log_func(f"Error during login for account {account_id}: {str(e)}")
            return False

    async def _type_with_human_delay(self, element: Any, text: str, log_func: Callable[[str], None]) -> None:
        """Simulates human-like typing with random delays."""
        for char in text:
            await element.type(char, delay=0)
            await asyncio.sleep(random.uniform(0.05, 0.3))