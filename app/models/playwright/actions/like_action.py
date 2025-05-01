import asyncio
import re
from typing import Any, Callable, Dict, Optional, Tuple

from ..base_action import AutomationAction
from ..browser_manager import BrowserManager


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

        browser_manager = BrowserManager()
        chromium_exe = browser_manager.get_chromium_executable(log_func)
        if not chromium_exe:
            log_func(f"No chromium executable found for account {account_id}")
            return False

        user_data_dir = browser_manager.get_session_dir(account_id)
        log_func(f"Starting Like action for account {account_id}")

        created_browser, playwright, browser = await self._initialize_browser(
            account_id, browser, user_data_dir, log_func
        )
        try:
            page = await browser.new_page()
            if not await self._navigate_to_url(page, url, account_id, log_func):
                return False

            overlay = await self._wait_for_post_overlay(page, account_id, log_func, debug)
            if overlay:
                await self._scroll_to_button(overlay, page, account_id, debug, log_func)
                like_button, button_name = await self._find_like_button(overlay, account_id, debug, log_func)
                if not like_button:
                    return False
            else:
                log_func(f"No overlay found, scrolling main page for Like button for account {account_id}")
                like_button, button_name = await self._find_like_button_on_main_page(page, account_id, debug, log_func)
                if not like_button:
                    return False

            if not await self._click_button(like_button, button_name, account_id, debug, log_func):
                return False

            return await self._verify_and_cleanup(
                page, like_button, account_id, created_browser, browser, log_func, debug
            )

        except Exception as e:
            log_func(f"Error during Like action for account {account_id}: {str(e)}")
            return False
        finally:
            await self._cleanup_browser(created_browser, browser, playwright, account_id, log_func)

    async def _initialize_browser(
        self, account_id: str, browser: Optional[Any], user_data_dir: str, log_func: Callable
    ) -> Tuple[bool, Optional[Any], Any]:
        """Initialize or reuse a browser context."""
        created_browser = False
        playwright = None
        from patchright.async_api import async_playwright

        try:
            if browser and not (hasattr(browser, '_closed') and browser._closed):
                log_func(f"Reusing browser context for account {account_id}")
            else:
                playwright = await async_playwright().__aenter__()
                browser = await playwright.chromium.launch_persistent_context(
                    no_viewport=True,
                    channel="chrome",
                    headless=False,
                    user_data_dir=user_data_dir,
                )
                created_browser = True
                log_func(f"Created browser context for account {account_id}")
            return created_browser, playwright, browser
        except Exception as e:
            log_func(f"Failed to initialize browser for account {account_id}: {str(e)}")
            raise

    async def _navigate_to_url(
        self, page: Any, url: str, account_id: str, log_func: Callable
    ) -> bool:
        """Navigate to the specified URL."""
        try:
            await page.goto(url, wait_until="load", timeout=60000)
            return True
        except Exception as e:
            log_func(f"Navigation failed for account {account_id}: {str(e)}")
            return False

    async def _wait_for_post_overlay(
        self, page: Any, account_id: str, log_func: Callable, debug: bool = False
    ) -> Optional[Any]:
        """Wait for the post overlay to load, if present."""
        log_func(f"Checking for post overlay for account {account_id}")
        for attempt in range(3):
            try:
                overlay = await page.wait_for_selector(
                    'div[role="dialog"], div[aria-modal="true"], div[class*="modal"], div[class*="popup"]',
                    timeout=5000
                )
                if overlay:
                    like_button = await overlay.query_selector(
                        '[aria-label="Like"], [aria-label="React"], [aria-label="Me gusta"], [aria-label="Reaccionar"]'
                    )
                    if like_button:
                        log_func(f"Post overlay with Like/React button loaded for account {account_id} on attempt {attempt + 1}")
                        return overlay
                    else:
                        log_func(f"Overlay found but no Like/React button on attempt {attempt + 1} for account {account_id}")
                await asyncio.sleep(2.0)
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
                    log_func(f"DOM dialogs on attempt {attempt + 1}: {dom_info}")
                await asyncio.sleep(2.0)
        log_func(f"No overlay detected after 3 attempts for account {account_id}")
        return None

    async def _try_scroll(
        self, element: Any, name: str, distance: int, debug: bool, log_func: Callable
    ) -> bool:
        """Attempt to scroll an element by a specified distance."""
        try:
            if name == "Page":
                scroll_before = await element.evaluate("() => window.scrollY")
                await element.evaluate(f"window.scrollBy(0, {distance})")
                scroll_after = await element.evaluate("() => window.scrollY")
            else:
                scroll_before = await element.evaluate("el => el.scrollTop")
                await element.evaluate(f"el => el.scrollBy(0, {distance})")
                scroll_after = await element.evaluate("el => el.scrollTop")
            if debug:
                log_func(f"{name} scroll: {scroll_before} -> {scroll_after}")
            return scroll_after > scroll_before
        except Exception as e:
            if debug:
                log_func(f"Failed to scroll {name}: {str(e)}")
            return False

    async def _scroll_to_button(
        self, overlay: Any, page: Any, account_id: str, debug: bool, log_func: Callable
    ) -> None:
        """Scroll to ensure the Like/React button is in the viewport within the overlay."""
        try:
            scrolled = await self._try_scroll(overlay, "Overlay", 100, debug, log_func)
            if not scrolled and debug:
                log_func(f"No scrollable element responded for account {account_id}")
            await asyncio.sleep(1.0)
        except Exception as e:
            log_func(f"Error scrolling to button for account {account_id}: {str(e)}")

    async def _find_like_button(
        self, overlay: Any, account_id: str, debug: bool, log_func: Callable
    ) -> Tuple[Optional[Any], Optional[str]]:
        """Find the Like or React button in the overlay."""
        selectors = [
            {"type": "aria-label", "value": r"^(Like|Me gusta)$", "name": "Like"},
            {"type": "aria-label", "value": r"^(React|Reaccionar)$", "name": "React"},
        ]

        start_time = asyncio.get_event_loop().time()
        timeout = 30  # seconds

        try:
            await asyncio.sleep(0.5)  # Wait for rendering
            buttons = await overlay.query_selector_all('[role="button"][aria-label]')
            for btn in buttons:
                try:
                    aria_label = await btn.evaluate("(el) => el.getAttribute('aria-label')")
                    for selector in selectors:
                        if aria_label and re.match(selector["value"], aria_label):
                            await btn.evaluate("el => el.scrollIntoView({block: 'center', inline: 'center', behavior: 'smooth'})")
                            await asyncio.sleep(0.5)
                            is_enabled = await btn.is_enabled()
                            if debug:
                                box = await btn.bounding_box()
                                if box:
                                    log_func(f"{selector['name']} button bounding box: x={box['x']}, y={box['y']}, width={box['width']}, height={box['height']}")
                                    viewport = await overlay.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})")
                                    in_viewport = (
                                        box['x'] >= 0 and
                                        box['y'] >= 0 and
                                        box['x'] + box['width'] <= viewport['width'] and
                                        box['y'] + box['height'] <= viewport['height']
                                    )
                                    log_func(f"{selector['name']} button in viewport: {in_viewport}")
                                is_visible = await btn.is_visible()
                                log_func(f"{selector['name']} button - Visible: {is_visible}, Enabled: {is_enabled}")

                            if is_enabled:
                                log_func(f"Found {selector['name']} button for account {account_id}")
                                return btn, selector["name"]
                except Exception as e:
                    if debug:
                        log_func(f"Error evaluating {selector['name']} button: {str(e)}")
                    continue

            if debug:
                aria_labels = await overlay.evaluate(
                    "(el) => Array.from(el.querySelectorAll('[aria-label]')).map(e => e.getAttribute('aria-label'))"
                )
                log_func(f"Overlay aria-labels: {aria_labels}")

            log_func(f"No Like or React button found for account {account_id}")
            return None, None

        except Exception as e:
            log_func(f"Error finding Like button for account {account_id}: {str(e)}")
            return None, None
        finally:
            if asyncio.get_event_loop().time() - start_time > timeout:
                log_func(f"Timeout reached while finding Like button for account {account_id}")
                return None, None

    async def _find_like_button_on_main_page(
        self, page: Any, account_id: str, debug: bool, log_func: Callable
    ) -> Tuple[Optional[Any], Optional[str]]:
        """Scroll the main page once by 280 pixels and find the Like button."""
        selector = {"type": "text", "value": r"^(LIKE|Me gusta)$", "name": "Like"}

        try:
            await page.evaluate("window.scrollBy(0, 280)")
            if debug:
                log_func(f"Scrolled main page 280 pixels for account {account_id}")
            await asyncio.sleep(1.0)

            buttons = await page.query_selector_all('[role="button"]')
            for btn in buttons:
                try:
                    text_content = await btn.evaluate("(el) => el.textContent.trim().toUpperCase()")
                    aria_label = await btn.evaluate("(el) => el.getAttribute('aria-label') || ''")
                    if (text_content and re.match(selector["value"], text_content)) or (aria_label and re.match(r"^(Like|Me gusta)$", aria_label)):
                        await btn.evaluate("el => el.scrollIntoView({block: 'center', inline: 'center', behavior: 'smooth'})")
                        await asyncio.sleep(0.5)
                        is_enabled = await btn.is_enabled()
                        if debug:
                            box = await btn.bounding_box()
                            if box:
                                log_func(f"{selector['name']} button bounding box: x={box['x']}, y={box['y']}, width={box['width']}, height={box['height']}")
                                viewport = await page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})")
                                in_viewport = (
                                    box['x'] >= 0 and
                                    box['y'] >= 0 and
                                    box['x'] + box['width'] <= viewport['width'] and
                                    box['y'] + box['height'] <= viewport['height']
                                )
                                log_func(f"{selector['name']} button in viewport: {in_viewport}")
                            is_visible = await btn.is_visible()
                            log_func(f"{selector['name']} button - Text: {text_content}, Aria-label: {aria_label}, Visible: {is_visible}, Enabled: {is_enabled}")

                        if is_enabled:
                            log_func(f"Found {selector['name']} button on main page for account {account_id}")
                            return btn, selector["name"]
                except Exception as e:
                    if debug:
                        log_func(f"Error evaluating {selector['name']} button on main page: {str(e)}")

            if debug:
                all_buttons = await page.query_selector_all('[role="button"]')
                button_info = []
                for btn in all_buttons:
                    try:
                        text = await btn.evaluate("(el) => el.textContent.trim()")
                        aria = await btn.evaluate("(el) => el.getAttribute('aria-label') || ''")
                        button_info.append(f"Text: {text}, Aria-label: {aria}")
                    except:
                        pass
                log_func(f"All buttons on main page: {button_info}")

            log_func(f"No Like button found on main page for account {account_id}")
            return None, None

        except Exception as e:
            log_func(f"Error finding Like button on main page for account {account_id}: {str(e)}")
            return None, None

    async def _click_button(
        self, button: Any, button_name: str, account_id: str, debug: bool, log_func: Callable
    ) -> bool:
        """Attempt to click the specified button using multiple methods."""
        try:
            await asyncio.sleep(1.0)  # Wait for DOM stabilization
            await button.focus()
            log_func(f"Focused {button_name} button for account {account_id}")

            click_methods = [
                (
                    lambda: button.click(timeout=10000),
                    f"Clicked {button_name} button for account {account_id} (standard click, attempt {{}})",
                    f"Standard click failed for account {account_id} (attempt {{}}): {{}}"
                ),
                (
                    lambda: button.evaluate("el => el.click()"),
                    f"Clicked {button_name} button for account {account_id} (JavaScript click, attempt {{}})",
                    f"JavaScript click failed for account {account_id} (attempt {{}}): {{}}"
                ),
                (
                    lambda: button.evaluate(
                        """el => {
                            const event = new MouseEvent('click', {bubbles: true, cancelable: true});
                            el.dispatchEvent(event);
                        }"""
                    ),
                    f"Clicked {button_name} button for account {account_id} (dispatched click event, attempt {{}})",
                    f"Dispatched click event failed for account {account_id} (attempt {{}}): {{}}"
                ),
            ]

            for attempt in range(3):
                for click_fn, success_msg, error_msg in click_methods:
                    try:
                        await click_fn()
                        log_func(success_msg.format(attempt + 1))
                        if debug:
                            log_func(f"Pausing for 1.5 seconds to display Like action for account {account_id}")
                        await asyncio.sleep(1.5)  # Delay to show the Like action
                        return True
                    except Exception as e:
                        log_func(error_msg.format(attempt + 1, str(e)))
                if attempt < 2:
                    await asyncio.sleep(1.0)

            if debug:
                parent_html = await button.evaluate("(element) => element.parentElement.outerHTML")
                log_func(f"Parent HTML of {button_name} button: {parent_html}")
            log_func(f"All click attempts failed for {button_name} button for account {account_id}")
            return False
        except Exception as e:
            log_func(f"Error during click attempt for {button_name} button for account {account_id}: {str(e)}")
            return False

    async def _verify_and_cleanup(
        self,
        page: Any,
        button: Any,
        account_id: str,
        created_browser: bool,
        browser: Any,
        log_func: Callable,
        debug: bool
    ) -> bool:
        """Verify the click action and close the browser if created."""
        try:
            # Single verification attempt
            await asyncio.sleep(1.0)
            try:
                button = await page.query_selector(
                    '[aria-label="Unlike"], [aria-label="No me gusta"], '
                    '[aria-label="Like"], [aria-label="Me gusta"], '
                    '[aria-label="React"], [aria-label="Reaccionar"]'
                )
                if not button:
                    log_func(f"No button found for verification for account {account_id}")
                else:
                    is_liked = await button.evaluate(
                        "(el) => el.getAttribute('aria-label')?.includes('Unlike') || el.getAttribute('aria-label')?.includes('No me gusta')"
                    )
                    if debug:
                        class_list = await button.evaluate("(el) => Array.from(el.classList)")
                        log_func(f"Button classes on verification: {class_list}")
                    log_func(
                        f"Like action {'successful' if is_liked else 'may not have succeeded'} for account {account_id}"
                    )
            except Exception as e:
                log_func(f"Failed to verify Like action for account {account_id}: {str(e)}")

        except Exception as e:
            log_func(f"Error during verification for account {account_id}: {str(e)}")

        try:
            if created_browser:
                if debug:
                    pages = await browser.pages()
                    log_func(f"Open pages before closing browser for account {account_id}: {len(pages)}")
                log_func(f"Preparing to close browser for account {account_id}")
                await asyncio.sleep(1.0)
                await browser.close()
                log_func(f"Closed browser for account {account_id}")
        except Exception as e:
            log_func(f"Error closing browser for account {account_id}: {str(e)}")
        return True

    async def _cleanup_browser(
        self,
        created_browser: bool,
        browser: Optional[Any],
        playwright: Optional[Any],
        account_id: str,
        log_func: Callable
    ) -> None:
        """Clean up browser and Playwright resources."""
        try:
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
        except Exception as e:
            log_func(f"Error during browser cleanup for account {account_id}: {str(e)}")