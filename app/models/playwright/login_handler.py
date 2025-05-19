import asyncio
import random
from typing import Any, Callable

from app.utils.config import LOGIN_POST_LOAD_DELAY
from app.utils.randomizer import Randomizer


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
        captcha_timeout: int = 60,
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
            login_button = await page.wait_for_selector(
                'button[name="login"]', timeout=30000
            )
            if login_button:
                await asyncio.sleep(random.uniform(2.0, 5.0))
                await login_button.click()
                log_func(f"Clicked login button for account {account_id}")
            else:
                log_func(f"Login button not found for account {account_id}")
                return False

            # Wait for page to stabilize
            await Randomizer.sleep(*LOGIN_POST_LOAD_DELAY)
            current_url = page.url

            # Check for CAPTCHA or checkpoint (2FA)
            if (
                "/checkpoint/" in current_url
                or "/two_step_verification/" in current_url
            ):
                log_func(
                    f"CAPTCHA or 2FA checkpoint detected for account {account_id}. Waiting {captcha_timeout} seconds for resolution..."
                )
                await asyncio.sleep(captcha_timeout)
                current_url = page.url
                if (
                    "/checkpoint/" in current_url
                    or "/two_step_verification/" in current_url
                ):
                    log_func(
                        f"CAPTCHA/2FA checkpoint not resolved for account {account_id} after {captcha_timeout} seconds"
                    )
                    return False
                log_func(
                    f"CAPTCHA/2FA checkpoint resolved for account {account_id}, proceeding to check login state"
                )

            # Verify no login form and correct URL
            login_form = await page.query_selector("input#email")
            if login_form:
                log_func(f"Login form detected for account {account_id}, login failed")
                return False
            if page.url != "https://www.facebook.com/":
                log_func(
                    f"Unexpected URL for account {account_id}: {page.url}, login failed"
                )
                return False

            # Check for "What's on your mind" text
            try:
                await page.wait_for_selector(
                    '//div[contains(text(), "What\'s on your mind")]', timeout=30000
                )
                log_func(
                    f"'What's on your mind' text found for account {account_id}, login successful"
                )
                return True
            except Exception as e:
                log_func(
                    f"Login failed for account {account_id}: 'What's on your mind' text not found - {str(e)}"
                )
                return False
        except Exception as e:
            log_func(f"Error during login for account {account_id}: {str(e)}")
            return False

    async def _type_with_human_delay(
        self, element: Any, text: str, log_func: Callable[[str], None]
    ) -> None:
        """Simulates human-like typing with random delays."""
        for char in text:
            await element.type(char, delay=0)
            await asyncio.sleep(random.uniform(0.05, 0.3))
