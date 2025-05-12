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
        debug = action_data.get("debug", True)

        if not url:
            log_func(f"No URL provided for Comment action on account {account_id}")
            return False

        # Default comments
        comments = ["Great post!", "Nice!", "Thanks for sharing!"]
        if comments_file:
            try:
                with open(comments_file, "r", encoding="utf-8") as f:
                    file_comments = [line.strip() for line in f.readlines() if line.strip()]
                    if file_comments:
                        comments = file_comments
            except Exception as e:
                log_func(f"Error loading comments file for account {account_id}: {str(e)}")

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
            from playwright.async_api import async_playwright

            if browser and not (hasattr(browser, '_closed') and browser._closed):
                log_func(f"Reusing existing browser context for account {account_id}")
            else:
                playwright = await async_playwright().__aenter__()
                browser = await playwright.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=False,
                    channel="chrome",
                )
                created_browser = True
                log_func(f"Created new browser context for account {account_id}")

            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=60000)
            log_func(f"Navigated to post URL for account {account_id}")

            # Check for login redirection
            if "login" in page.url.lower():
                log_func(f"Unexpected redirection to login page: {page.url}")
                return False

            # Wait for post overlay
            overlay = await self._wait_for_post_overlay(page, debug, account_id, log_func)
            comment_field = None
            if overlay:
                log_func(f"Overlay found, searching for comment field for account {account_id}")
                comment_field = await self._find_comment_field(overlay, debug, account_id, log_func)
            else:
                log_func(f"No overlay found, searching main page for comment field for account {account_id}")
                comment_field = await self._find_comment_field(page, debug, account_id, log_func)

            if not comment_field:
                log_func(f"Could not find comment field for account {account_id}")
                return False

            # Click and type the comment
            await comment_field.click()
            await self._type_with_human_delay(comment_field, comment_text, log_func)

            # Press Enter to submit
            await page.keyboard.press("Enter")
            log_func(f"Posted comment for account {account_id}: '{comment_text}'")

            # Verify comment
            success = await self._verify_comment(page, comment_text, debug, account_id, log_func)
            if not success:
                log_func(f"Comment verification failed for account {account_id}")
                return False

            return True

        except Exception as e:
            log_func(f"Error during Comment action for account {account_id}: {str(e)}")
            return False
        finally:
            if created_browser and browser and not (hasattr(browser, '_closed') and browser._closed):
                try:
                    await browser.close()
                    log_func(f"Closed browser for account {account_id}")
                except Exception as e:
                    log_func(f"Error closing browser for account {account_id}: {str(e)}")
            if playwright:
                try:
                    await playwright.__aexit__(None, None, None)
                    log_func(f"Closed Playwright instance for account {account_id}")
                except Exception as e:
                    log_func(f"Error closing Playwright instance for account {account_id}: {str(e)}")

    async def _wait_for_post_overlay(self, page: Any, debug: bool, account_id: str, log_func: Callable[[str], None]) -> Optional[Any]:
        """Wait for the post overlay to load, if present."""
        log_func(f"Checking for post overlay for account {account_id}")
        for attempt in range(4):
            try:
                overlay = await page.wait_for_selector(
                    'div[role="dialog"], div[aria-modal="true"], div[class*="modal"], div[class*="popup"]',
                    timeout=7000
                )
                if overlay and await overlay.query_selector(
                    '[aria-label*="comment" i], [placeholder*="comment" i], [role="textbox"][contenteditable="true"]'
                ):
                    log_func(f"Post overlay with comment field loaded on attempt {attempt + 1} for account {account_id}")
                    return overlay
                log_func(f"Overlay found but no comment field on attempt {attempt + 1} for account {account_id}")
                await asyncio.sleep(3.0)
            except Exception:
                log_func(f"No overlay detected on attempt {attempt + 1} for account {account_id}")
                if debug:
                    dom_info = await page.evaluate("""
                        () => {
                            const dialogs = document.querySelectorAll('div[role="dialog"], div[aria-modal="true"], div[class*="modal"], div[class*="popup"]');
                            return Array.from(dialogs).map(d => ({
                                outerHTML: d.outerHTML.slice(0, 200),
                                ariaLabels: Array.from(d.querySelectorAll('[aria-label]')).map(e => e.getAttribute('aria-label'))
                            }));
                        }
                    """)
                    log_func(f"DOM dialogs on attempt {attempt + 1} for account {account_id}: {dom_info}")
                await asyncio.sleep(3.0)
        log_func(f"No overlay detected after 4 attempts for account {account_id}")
        return None

    async def _find_comment_field(self, context: Any, debug: bool, account_id: str, log_func: Callable[[str], None]) -> Optional[Any]:
        """Find the comment field in the given context (overlay or main page)."""
        comment_selectors = [
            'div[aria-label*="Write a comment" i], div[aria-label*="Escribe un comentario" i]',  # Prioritize aria-label
            'div[role="textbox"][contenteditable="true"]',  # Fallback
            'textarea[placeholder*="Write a comment" i], textarea[placeholder*="Escribe un comentario" i]',
            'form[data-testid*="ComposerForm"]',
            'div[data-testid*="comment"]',
        ]

        for attempt in range(4):
            for selector in comment_selectors:
                try:
                    log_func(f"Attempt {attempt + 1}: Trying selector {selector} for account {account_id}")
                    comment_field = await context.wait_for_selector(selector, timeout=10000)
                    if comment_field:
                        is_enabled = await comment_field.is_enabled()
                        is_visible = await comment_field.is_visible()
                        is_js_visible = await comment_field.evaluate(
                            """el => {
                                const rect = el.getBoundingClientRect();
                                return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).display !== 'none';
                            }"""
                        )
                        if debug:
                            log_func(
                                f"Comment field found with selector {selector}: Visible={is_visible}, JS_Visible={is_js_visible}, Enabled={is_enabled} for account {account_id}"
                            )
                        if is_enabled and (is_visible or is_js_visible):
                            log_func(f"Found comment field with selector {selector} for account {account_id}")
                            return comment_field
                        log_func(f"Comment field not interactable (Visible={is_visible}, JS_Visible={is_js_visible}) for account {account_id}")
                    else:
                        log_func(f"Selector {selector} returned no element for account {account_id}")
                except Exception as e:
                    log_func(f"Attempt {attempt + 1}: Selector {selector} failed: {str(e)} for account {account_id}")
            if attempt < 3:
                log_func(f"Waiting 5s before retries for account {account_id}")
                await asyncio.sleep(5)

        if debug:
            aria_labels = await context.evaluate(
                "(el) => Array.from(el.querySelectorAll('[aria-label]')).map(e => e.getAttribute('aria-label'))"
            )
            log_func(f"Context aria-labels for account {account_id}: {aria_labels}")
        log_func(f"No comment field found after 4 attempts for account {account_id}")
        return None

    async def _type_with_human_delay(self, element: Any, text: str, log_func: Callable[[str], None]) -> None:
        """Simulates human-like typing with random delays and pauses."""
        for i, char in enumerate(text):
            await element.type(char, delay=random.uniform(0.05, 0.2))
            if i % 5 == 0 and i > 0:  # Random pause every few characters
                await asyncio.sleep(random.uniform(0.3, 0.7))
            await asyncio.sleep(random.uniform(0.05, 0.15))

    async def _verify_comment(self, page: Any, comment_text: str, debug: bool, account_id: str, log_func: Callable[[str], None]) -> bool:
        """Verify that the comment was posted."""
        try:
            await asyncio.sleep(3.0)  # Wait for comment to appear
            comment_selector = f'//div[contains(text(), "{comment_text}")]'
            comment_element = await page.wait_for_selector(comment_selector, timeout=10000)
            if comment_element:
                log_func(f"Comment '{comment_text}' verified on page for account {account_id}")
                return True
            log_func(f"Comment '{comment_text}' not found on page for account {account_id}")
            return False
        except Exception as e:
            log_func(f"Error verifying comment for account {account_id}: {str(e)}")
            return False