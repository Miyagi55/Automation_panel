import asyncio
import random
from typing import Any, Callable, Dict, Optional, Tuple

from ..base_action import AutomationAction
from ..browser_manager import BrowserManager


class CommentButtonLocator:
    """Handles detection and clicking of the Comment button for videos and live posts."""

    @staticmethod
    async def find_and_click_comment_button(
        page: Any, debug: bool, account_id: str, log_func: Callable[[str], None]
    ) -> bool:
        """Find and click the Comment button on the main page after scrolling."""
        log_func(f"Scrolling to find Comment button for account {account_id}")
        await page.evaluate("window.scrollBy(0, 300)")  # Small scroll to reveal button
        await asyncio.sleep(1.0)

        comment_button_selectors = [
            '[aria-label="Comment" i], [aria-label="Comentar" i]',  # Prioritize aria-label
            '[role="button"]:has-text("Comment"), [role="button"]:has-text("Comentar")',  # Text-based fallback
        ]

        for attempt in range(3):
            for selector in comment_button_selectors:
                try:
                    log_func(f"Attempt {attempt + 1}: Trying Comment button selector {selector} for account {account_id}")
                    button = await page.wait_for_selector(selector, timeout=5000)
                    if button:
                        is_enabled = await button.is_enabled()
                        is_visible = await button.is_visible()
                        is_js_visible = await button.evaluate(
                            """el => {
                                const rect = el.getBoundingClientRect();
                                return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).display !== 'none';
                            }"""
                        )
                        if debug:
                            log_func(
                                f"Comment button found with selector {selector}: Visible={is_visible}, JS_Visible={is_js_visible}, Enabled={is_enabled} for account {account_id}"
                            )
                        if is_enabled and (is_visible or is_js_visible):
                            await button.click()
                            log_func(f"Clicked Comment button with selector {selector} for account {account_id}")
                            await asyncio.sleep(1.0)  # Wait for comment field to appear
                            return True
                        log_func(f"Comment button not interactable (Visible={is_visible}, JS_Visible={is_js_visible}) for account {account_id}")
                    else:
                        log_func(f"Selector {selector} returned no element for account {account_id}")
                except Exception as e:
                    log_func(f"Attempt {attempt + 1}: Comment button selector {selector} failed: {str(e)} for account {account_id}")
            if attempt < 2:
                log_func(f"Waiting 2s before retrying Comment button for account {account_id}")
                await asyncio.sleep(2.0)

        log_func(f"No Comment button found after 3 attempts, proceeding to find comment field for account {account_id}")
        return False  # Allow proceeding to comment field detection


class CommentFieldLocator:
    """Handles detection of post overlays and comment fields."""

    @staticmethod
    async def wait_for_post_overlay(
        page: Any, debug: bool, account_id: str, log_func: Callable[[str], None]
    ) -> Optional[Any]:
        """Wait for post overlay to load, if present."""
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

    @staticmethod
    async def find_comment_field(
        context: Any, is_video: bool, debug: bool, account_id: str, log_func: Callable[[str], None]
    ) -> Optional[Any]:
        """Find the comment field in the given context (overlay, main page, or video/live-specific)."""
        comment_selectors = [
            'div[aria-label*="Write a comment" i], div[aria-label*="Escribe un comentario" i]',
            'div[role="textbox"][contenteditable="true"]',
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


class CommentWriter:
    """Handles typing and submitting comments."""

    @staticmethod
    async def type_with_human_delay(
        element: Any, text: str, log_func: Callable[[str], None]
    ) -> None:
        """Simulates human-like typing with random delays and pauses."""
        for i, char in enumerate(text):
            await element.type(char, delay=random.uniform(0.05, 0.2))
            if i % 5 == 0 and i > 0:  # Random pause every few characters
                await asyncio.sleep(random.uniform(0.3, 0.7))
            await asyncio.sleep(random.uniform(0.05, 0.15))

    @staticmethod
    async def submit_comment(
        page: Any, comment_field: Any, comment_text: str, account_id: str, log_func: Callable[[str], None]
    ) -> None:
        """Clicks the comment field, types the comment, and submits it."""
        await comment_field.click()
        await CommentWriter.type_with_human_delay(comment_field, comment_text, log_func)
        await page.keyboard.press("Enter")
        log_func(f"Posted comment for account {account_id}: '{comment_text}'")


class CommentVerifier:
    """Verifies that a comment was posted successfully."""

    @staticmethod
    async def verify_comment(
        page: Any, comment_text: str, debug: bool, account_id: str, log_func: Callable[[str], None]
    ) -> bool:
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


class CommentAction(AutomationAction):
    """Automation action for commenting on Facebook posts, videos, and live streams."""

    def __init__(self):
        super().__init__("Comments")
        self._field_locator = CommentFieldLocator()
        self._comment_writer = CommentWriter()
        self._comment_verifier = CommentVerifier()
        self._button_locator = CommentButtonLocator()

    async def execute(
        self,
        account_id: str,
        account_data: Dict[str, Any],
        action_data: Dict[str, Any],
        log_func: Callable[[str], None],
        browser: Optional[Any] = None,
    ) -> bool:
        """Execute the comment action on a post, video, or live stream."""
        comment_text = await self._load_comment_text(action_data, account_id, log_func)
        if not comment_text:
            return False

        browser, page, created_browser, playwright = await self._setup_browser(
            account_id, action_data, browser, log_func
        )
        if not browser or not page:
            return False

        try:
            if not await self._navigate_to_post(page, action_data.get("link", ""), account_id, log_func):
                return False

            comment_field = await self._locate_comment_field(page, action_data.get("debug", True), account_id, log_func)
            if not comment_field:
                return False

            await self._comment_writer.submit_comment(page, comment_field, comment_text, account_id, log_func)

            return await self._comment_verifier.verify_comment(
                page, comment_text, action_data.get("debug", True), account_id, log_func
            )

        except Exception as e:
            log_func(f"Error during Comment action for account {account_id}: {str(e)}")
            return False
        finally:
            await self._cleanup_browser(created_browser, browser, playwright, account_id, log_func)

    async def _load_comment_text(
        self, action_data: Dict[str, Any], account_id: str, log_func: Callable[[str], None]
    ) -> Optional[str]:
        """Load a random comment from the provided file or default comments."""
        url = action_data.get("link", "")
        comments_file = action_data.get("comments_file", None)
        if not url:
            log_func(f"No URL provided for Comment action on account {account_id}")
            return None



################# Default messages in case there is no comments uploaded!!!!####################################
        comments = ["Great post!", "Nice!", "Thanks for sharing!"]
        if comments_file:
            try:
                with open(comments_file, "r", encoding="utf-8") as f:
                    file_comments = [line.strip() for line in f.readlines() if line.strip()]
                    if file_comments:
                        comments = file_comments
            except Exception as e:
                log_func(f"Error loading comments file for account {account_id}: {str(e)}")

        return random.choice(comments)

    async def _setup_browser(
        self,
        account_id: str,
        action_data: Dict[str, Any],
        browser: Optional[Any],
        log_func: Callable[[str], None],
    ) -> Tuple[Optional[Any], Optional[Any], bool, Optional[Any]]:
        """Set up the browser and page for the comment action."""
        browser_manager = BrowserManager()
        chromium_exe = browser_manager.get_chromium_executable(log_func)
        if not chromium_exe:
            log_func(f"No chromium executable found for account {account_id}")
            return None, None, False, None

        user_data_dir = browser_manager.get_session_dir(account_id)
        log_func(f"Starting Comment action for account {account_id} on {action_data.get('link', '')}")

        created_browser = False
        playwright = None
        page = None

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
            return browser, page, created_browser, playwright

        except Exception as e:
            log_func(f"Error setting up browser for account {account_id}: {str(e)}")
            await self._cleanup_browser(created_browser, browser, playwright, account_id, log_func)
            return None, None, False, None

    async def _navigate_to_post(
        self, page: Any, url: str, account_id: str, log_func: Callable[[str], None]
    ) -> bool:
        """Navigate to the post URL and check for login redirection."""
        await page.goto(url, wait_until="networkidle", timeout=60000)
        log_func(f"Navigated to post URL for account {account_id}")

        if "login" in page.url.lower():
            log_func(f"Unexpected redirection to login page: {page.url}")
            return False
        return True

    async def _detect_post_type(
        self, page: Any, debug: bool, account_id: str, log_func: Callable[[str], None]
    ) -> str:
        """Detect if the post is a normal post, video, or live stream."""
        try:
            # Check for video
            video_element = await page.query_selector('video')
            if video_element:
                log_func(f"Detected video post for account {account_id}")
                return "video"

            # Check for live indicators
            live_indicator = await page.query_selector('[aria-label*="Live" i], [class*="live"]')
            if live_indicator:
                log_func(f"Detected live post for account {account_id}")
                return "live"

            log_func(f"Detected normal post for account {account_id}")
            return "normal"
        except Exception as e:
            log_func(f"Error detecting post type for account {account_id}: {str(e)}")
            return "normal"  # Fallback to normal post

    async def _locate_comment_field(
        self, page: Any, debug: bool, account_id: str, log_func: Callable[[str], None]
    ) -> Optional[Any]:
        """Locate the comment field, handling normal posts, videos, and live streams."""
        post_type = await self._detect_post_type(page, debug, account_id, log_func)

        if post_type == "normal":
            # Try overlay for normal posts
            overlay = await self._field_locator.wait_for_post_overlay(page, debug, account_id, log_func)
            if overlay:
                log_func(f"Overlay found, searching for comment field for account {account_id}")
                return await self._field_locator.find_comment_field(overlay, False, debug, account_id, log_func)
            log_func(f"No overlay found, searching main page for comment field for account {account_id}")
            return await self._field_locator.find_comment_field(page, False, debug, account_id, log_func)
        else:
            # Handle videos and lives
            await self._button_locator.find_and_click_comment_button(page, debug, account_id, log_func)
            # For lives, the comment field appears on the right; for videos, it’s already visible
            context = page
            return await self._field_locator.find_comment_field(context, False, debug, account_id, log_func)

    async def _cleanup_browser(
        self,
        created_browser: bool,
        browser: Optional[Any],
        playwright: Optional[Any],
        account_id: str,
        log_func: Callable[[str], None],
    ) -> None:
        """Clean up browser and Playwright resources."""
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