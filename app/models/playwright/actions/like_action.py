import asyncio
import re
from typing import Any, Callable, Dict, Optional, Tuple

from app.utils.config import LIKE_ACTION_DELAY_RANGE
from app.utils.randomizer import Randomizer

from ..base_action import AutomationAction
from .base_selectors import FacebookSelectors
from .element_utils import ElementUtils


class ButtonSelector:
    """Encapsulates button selector definitions for Like and React buttons."""

    SELECTORS = [
        {"type": "aria-label", "value": r"^(Like|Me gusta)$", "name": "Like"},
        {"type": "aria-label", "value": r"^(React|Reaccionar)$", "name": "React"},
    ]
    MAIN_PAGE_SELECTOR = {"type": "text", "value": r"^(LIKE|Me gusta)$", "name": "Like"}


class LikeAction(AutomationAction):
    """Automation action for liking Facebook posts."""

    def __init__(self):
        super().__init__("Likes")

    async def execute(
        self,
        account_id: str,
        account_data: Dict[str, Any],
        action_data: Dict[str, Any],
        log_func: Callable[[str], None],
        browser: Optional[Any] = None,
    ) -> bool:
        """Execute the like action on a Facebook post."""
        url = action_data.get("link", "")
        debug = action_data.get("debug", True)
        if not url:
            log_func(f"No URL provided for Like action on account {account_id}")
            return False

        self.log_func = log_func
        self.account_id = account_id

        log_func(f"Starting Like action for account {account_id}")

        try:
            # Import browser utils
            from .browser_utils import BrowserUtils

            browser_utils = BrowserUtils(account_id, log_func)
            user_data_dir = browser_utils.get_session_dir()

            (
                created_browser,
                playwright,
                browser,
            ) = await browser_utils.initialize_browser(browser, user_data_dir)

            page = await browser.new_page()

            # Navigate to URL
            await page.goto(url, wait_until="networkidle", timeout=60000)
            log_func(f"Successfully navigated to URL (account {account_id})")

            # Add small delay to let page settle
            await Randomizer.sleep(*LIKE_ACTION_DELAY_RANGE)

            # Try to find like button using element utils
            element_utils = ElementUtils(log_func)

            # First try to find like button directly on the page
            like_button = await element_utils.finder.find_element_by_selector_group(
                page, FacebookSelectors.LIKE_BUTTONS, account_id=account_id
            )

            if not like_button:
                # Try overlay approach
                overlay = await self._wait_for_post_overlay(page, debug)
                if overlay:
                    like_button, button_name = await self._find_like_button(
                        overlay, debug
                    )
                else:
                    # Try scrolling main page approach
                    log_func(
                        f"No overlay found, scrolling main page for Like button for account {account_id}"
                    )
                    (
                        like_button,
                        button_name,
                    ) = await self._find_like_button_on_main_page(page, debug)

            if not like_button:
                log_func(f"No like button found on page (account {account_id})")
                return False

            # Click the like button using element utils
            click_success = await element_utils.clicker.click_element(
                like_button, "Like button", account_id
            )

            if not click_success:
                log_func(f"Failed to click like button (account {account_id})")
                return False

            # Wait for the action to complete
            await Randomizer.sleep(0.5, 1.5)
            log_func(f"Like action completed successfully (account {account_id})")

            # Optional verification
            await Randomizer.sleep(0.5, 1.0)
            unlike_button = await element_utils.finder.find_element_by_selector_group(
                page,
                FacebookSelectors.UNLIKE_BUTTONS,
                account_id=account_id,
                timeout=3000,
            )

            if unlike_button:
                log_func(f"Like action verified successfully (account {account_id})")
            else:
                log_func(
                    f"Like action verification inconclusive (account {account_id})"
                )

            return True

        except Exception as e:
            log_func(f"Like action failed: {str(e)} (account {account_id})")
            return False
        finally:
            # Cleanup
            try:
                if "browser_utils" in locals():
                    await browser_utils.cleanup_browser(
                        created_browser, browser, playwright
                    )
            except Exception as e:
                log_func(f"Error during cleanup for account {account_id}: {str(e)}")

    async def _wait_for_post_overlay(self, page: Any, debug: bool) -> Optional[Any]:
        """Wait for the post overlay to load, if present."""
        self._log_info("Checking for post overlay")
        for attempt in range(3):
            try:
                overlay = await page.wait_for_selector(
                    'div[role="dialog"], div[aria-modal="true"], div[class*="modal"], div[class*="popup"]',
                    timeout=5000,
                )
                if overlay and await overlay.query_selector(
                    '[aria-label="Like"], [aria-label="React"], [aria-label="Me gusta"], [aria-label="Reaccionar"]'
                ):
                    self._log_info(
                        f"Post overlay with Like/React button loaded on attempt {attempt + 1}"
                    )
                    return overlay
                self._log_info(
                    f"Overlay found but no Like/React button on attempt {attempt + 1}"
                )
                await Randomizer.sleep(*LIKE_ACTION_DELAY_RANGE)
            except Exception:
                self._log_info(f"No overlay detected on attempt {attempt + 1}")
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
                    self._log_info(f"DOM dialogs on attempt {attempt + 1}: {dom_info}")
                await Randomizer.sleep(*LIKE_ACTION_DELAY_RANGE)
        self._log_info("No overlay detected after 3 attempts")
        return None

    async def _find_like_button(
        self, overlay: Any, debug: bool
    ) -> Tuple[Optional[Any], Optional[str]]:
        """Find the Like or React button in the overlay."""
        start_time = asyncio.get_event_loop().time()
        timeout = 30

        try:
            await Randomizer.sleep(*LIKE_ACTION_DELAY_RANGE)
            buttons = await overlay.query_selector_all('[role="button"][aria-label]')
            for btn in buttons:
                button, button_name = await self._evaluate_button_state(
                    btn, ButtonSelector.SELECTORS, debug
                )
                if button and button_name:
                    return button, button_name

            if debug:
                aria_labels = await overlay.evaluate(
                    "(el) => Array.from(el.querySelectorAll('[aria-label]')).map(e => e.getAttribute('aria-label'))"
                )
                self._log_info(f"Overlay aria-labels: {aria_labels}")

            self._log_info("No Like or React button found")
            return None, None

        except Exception as e:
            self._log_error(f"Error finding Like button: {str(e)}")
            return None, None
        finally:
            if asyncio.get_event_loop().time() - start_time > timeout:
                self._log_info("Timeout reached while finding Like button")
                return None, None

    async def _find_like_button_on_main_page(
        self, page: Any, debug: bool
    ) -> Tuple[Optional[Any], Optional[str]]:
        """Scroll the main page once by 280 pixels and find the Like button."""
        try:
            await page.evaluate("window.scrollBy(0, 280)")
            if debug:
                self._log_info("Scrolled main page 280 pixels")
            await Randomizer.sleep(*LIKE_ACTION_DELAY_RANGE)

            buttons = await page.query_selector_all('[role="button"]')
            for btn in buttons:
                button, button_name = await self._evaluate_button_state(
                    btn, [ButtonSelector.MAIN_PAGE_SELECTOR], debug, is_main_page=True
                )
                if button and button_name:
                    return button, button_name

            if debug:
                button_info = []
                for btn in await page.query_selector_all('[role="button"]'):
                    try:
                        text = await btn.evaluate("(el) => el.textContent.trim()")
                        aria = await btn.evaluate(
                            "(el) => el.getAttribute('aria-label') || ''"
                        )
                        button_info.append(f"Text: {text}, Aria-label: {aria}")
                    except:
                        pass
                self._log_info(f"All buttons on main page: {button_info}")

            self._log_info("No Like button found on main page")
            return None, None

        except Exception as e:
            self._log_error(f"Error finding Like button on main page: {str(e)}")
            return None, None

    async def _evaluate_button_state(
        self, btn: Any, selectors: list, debug: bool, is_main_page: bool = False
    ) -> Tuple[Optional[Any], Optional[str]]:
        """Evaluate if a button matches the selector criteria."""
        try:
            text_content = (
                (
                    await btn.evaluate("(el) => el.textContent.trim().toUpperCase()")
                ).strip()
                if is_main_page
                else ""
            )
            aria_label = await btn.evaluate(
                "(el) => el.getAttribute('aria-label') || ''"
            )
            for selector in selectors:
                if (
                    is_main_page
                    and text_content
                    and re.match(selector["value"], text_content)
                ) or (aria_label and re.match(selector["value"], aria_label)):
                    await self._ensure_element_in_viewport(btn, selector["name"], debug)
                    is_enabled = await btn.is_enabled()
                    if debug:
                        await self._log_button_debug_info(
                            btn, selector["name"], text_content, aria_label, is_enabled
                        )
                    if is_enabled:
                        self._log_info(f"Found {selector['name']} button")
                        return btn, selector["name"]
        except Exception as e:
            if debug:
                self._log_error(f"Error evaluating {selector['name']} button: {str(e)}")
        return None, None

    async def _ensure_element_in_viewport(
        self, btn: Any, name: str, debug: bool
    ) -> None:
        """Ensure the button is in the viewport."""
        await btn.evaluate(
            "el => el.scrollIntoView({block: 'center', inline: 'center', behavior: 'smooth'})"
        )
        await Randomizer.sleep(*LIKE_ACTION_DELAY_RANGE)
        if debug:
            box = await btn.bounding_box()
            if box:
                viewport = await btn.evaluate(
                    "() => ({width: window.innerWidth, height: window.innerHeight})"
                )
                in_viewport = (
                    box["x"] >= 0
                    and box["y"] >= 0
                    and box["x"] + box["width"] <= viewport["width"]
                    and box["y"] + box["height"] <= viewport["height"]
                )
                self._log_info(
                    f"{name} button bounding box: x={box['x']}, y={box['y']}, width={box['width']}, height={box['height']}"
                )
                self._log_info(f"{name} button in viewport: {in_viewport}")

    async def _log_button_debug_info(
        self, btn: Any, name: str, text_content: str, aria_label: str, is_enabled: bool
    ) -> None:
        """Log debug information for a button."""
        is_visible = await btn.is_visible()
        self._log_info(
            f"{name} button - Text: {text_content}, Aria-label: {aria_label}, Visible: {is_visible}, Enabled: {is_enabled}"
        )

    def _log_info(self, message: str) -> None:
        """Log an info message with account ID."""
        if hasattr(self, "log_func") and hasattr(self, "account_id"):
            self.log_func(f"{message} for account {self.account_id}")

    def _log_error(self, message: str) -> None:
        """Log an error message with account ID."""
        self._log_info(f"Error: {message}")
