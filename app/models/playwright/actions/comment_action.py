import asyncio
import random
from typing import Any, Callable, Dict, Optional

from ..base_action import AutomationAction
from ..browser_manager import BrowserManager


class CommentAction(AutomationAction):
    """Automation action for commenting on Facebook posts."""

    def __init__(self):
        super().__init__("Comments")

    async def execute(
        self,
        account_id: str,
        account_data: Dict[str, Any],
        action_data: Dict[str, Any],
        log_func: Callable[[str], None],
        browser: Optional[Any] = None,
    ) -> bool:
        """Execute the comment action on a post."""
        url = action_data.get("link", "")
        comments_file = action_data.get("comments_file", None)

        if not url:
            log_func(f"No URL provided for Comment action on account {account_id}")
            return False

        comments = ["Great post!", "Nice!", "Thanks for sharing!"]
        if comments_file:
            try:
                with open(comments_file, "r") as f:
                    file_comments = [
                        line.strip() for line in f.readlines() if line.strip()
                    ]
                    if file_comments:
                        comments = file_comments
            except Exception as e:
                log_func(
                    f"Error loading comments file for account {account_id}: {str(e)}"
                )

        comment_text = random.choice(comments)

        browser_manager = BrowserManager()
        chromium_exe = browser_manager.get_chromium_executable(log_func)
        if not chromium_exe:
            log_func(f"No chromium executable found for account {account_id}")
            return False

        user_data_dir = browser_manager.get_session_dir(account_id)
        log_func(f"Starting Comment action for account {account_id} on {url}")

        created_browser = False
        playwright = None
        try:
            from patchright.async_api import async_playwright

            if browser and not (hasattr(browser, '_closed') and browser._closed):
                log_func(f"Reusing existing browser context for account {account_id}")
            else:
                playwright = await async_playwright().__aenter__()
                browser = await playwright.chromium.launch_persistent_context(
                    no_viewport=True,
                    channel="chrome",
                    headless=False,
                    user_data_dir=user_data_dir,
                )
                created_browser = True
                log_func(f"Created new browser context for account {account_id}")

            page = await browser.new_page()
            await page.goto(url, wait_until="load", timeout=60000)
            log_func(f"Navigated to post URL in new tab for account {account_id}")

            comment_selectors = [
                'div[aria-label="Write a comment"]',
                'div[data-testid="commentForm"]',
                'form[data-testid="UFI2ComposerForm"]',
            ]

            comment_field = None
            for selector in comment_selectors:
                try:
                    comment_field = await page.wait_for_selector(
                        selector, timeout=5000
                    )
                    if comment_field:
                        break
                except:
                    continue

            if not comment_field:
                log_func(f"Could not find comment field for account {account_id}")
                if created_browser:
                    await browser.close()
                return False

            await comment_field.click()

            await self._type_with_human_delay(comment_field, comment_text, log_func)

            await page.keyboard.press("Enter")
            log_func(f"Posted comment for account {account_id}")

            await asyncio.sleep(5)

            if created_browser:
                await browser.close()
            return True

        except Exception as e:
            log_func(f"Error during Comment action for account {account_id}: {str(e)}")
            return False
        finally:
            if created_browser and browser and not (hasattr(browser, '_closed') and browser._closed):
                try:
                    await browser.close()
                    log_func(f"Ensured browser closed for account {account_id}")
                except Exception as e:
                    log_func(f"Error closing browser for account {account_id}: {str(e)}")
            if playwright:
                try:
                    await playwright.__aexit__(None, None, None)
                    log_func(f"Closed Playwright instance for account {account_id}")
                except Exception as e:
                    log_func(f"Error closing Playwright instance for account {account_id}: {str(e)}")