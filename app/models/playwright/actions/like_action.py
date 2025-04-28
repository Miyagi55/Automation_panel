import asyncio
import random
import re
from typing import Any, Callable, Dict, Optional

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
        """Execute the like action on a post."""
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
        log_func(f"Starting Like action for account {account_id} on {url}")

        created_browser = False
        playwright = None
        try:
            from patchright.async_api import async_playwright # type: ignore

            if browser and not (hasattr(browser, '_closed') and browser._closed):
                log_func(f"Reusing existing browser context for account {account_id}")
            else:
                playwright = await async_playwright().__aenter__()
                browser = await playwright.chromium.launch_persistent_context(
                    no_viewport=True,
                    channel="chrome",
                    headless=False,
                    user_data_dir=user_data_dir,
 enquete=True
                )
                created_browser = True
                log_func(f"Created new browser context for account {account_id}")

            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="load", timeout=60000)
            except Exception as e:
                log_func(f"Navigation failed for account {account_id}: {str(e)}")
                return False

            log_func(f"Waiting for post overlay to load for account {account_id}")
            overlay = None
            for attempt in range(3):
                try:
                    overlay = await page.wait_for_selector(
                        'div[role="dialog"]:has([aria-label="Like"]), div[role="dialog"]:has([aria-label="React"])',
                        timeout=2000
                    )
                    if overlay:
                        break
                    log_func(f"Overlay not found on attempt {attempt + 1}/3 for account {account_id}")
                    await asyncio.sleep(2.0)
                except Exception as e:
                    log_func(f"Overlay wait failed on attempt {attempt + 1}/3 for account {account_id}: {str(e)}")
                    await asyncio.sleep(2.0)

            if not overlay:
                log_func(f"Could not find post overlay for account {account_id}")
                if created_browser:
                    await browser.close()
                return False

            await asyncio.sleep(2.0)
            log_func(f"Post overlay loaded for account {account_id}")

            # Robust scrolling logic
            async def try_scroll(element, name: str, distance: int = 280) -> bool:
                try:
                    scroll_before = await element.evaluate("el => el.scrollTop")
                    await element.evaluate(f"el => el.scrollBy(0, {distance})")
                    scroll_after = await element.evaluate("el => el.scrollTop")
                    if debug:
                        log_func(f"{name} scroll position: {scroll_before} -> {scroll_after}")
                    return scroll_after > scroll_before
                except Exception as e:
                    if debug:
                        log_func(f"Failed to scroll {name}: {str(e)}")
                    return False

            # Try scrolling overlay, parent, or page multiple times
            for _ in range(3):
                scrolled = await try_scroll(overlay, "Overlay")
                if not scrolled:
                    parent = await overlay.evaluate_handle("el => el.parentElement")
                    scrolled = await try_scroll(parent, "Overlay parent")
                if not scrolled:
                    scrolled = await try_scroll(page, "Page")
                if scrolled:
                    break
                await asyncio.sleep(1.0)
            else:
                if debug:
                    log_func("No scrollable element responded after multiple attempts")

            await asyncio.sleep(2.0)

            like_button = None
            selectors = [
                {"type": "aria-label", "value": r"^(Like|Me gusta)$", "name": "Like"},
                {"type": "aria-label", "value": r"^(React|Reaccionar)$", "name": "React"},
            ]

            for selector in selectors:
                try:
                    buttons = await overlay.query_selector_all("[aria-label]")
                    for btn in buttons:
                        try:
                            aria_label = await btn.evaluate("(el) => el.getAttribute('aria-label')")
                            if debug:
                                button_html = await btn.evaluate("(el) => el.outerHTML")
                                log_func(f"Evaluating {selector['name']} button with aria-label: '{aria_label}', HTML: {button_html[:100]}...")
                            if aria_label and re.match(selector["value"], aria_label):
                                # Scroll button into view
                                await btn.evaluate("el => el.scrollIntoView({block: 'center', inline: 'center', behavior: 'smooth'})")
                                # Check bounding box to confirm button is in viewport
                                try:
                                    box = await btn.bounding_box()
                                    if box:
                                        if debug:
                                            log_func(f"{selector['name']} button bounding box: x={box['x']}, y={box['y']}, width={box['width']}, height={box['height']}")
                                        viewport = await page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})")
                                        in_viewport = (
                                            box['x'] >= 0 and
                                            box['y'] >= 0 and
                                            box['x'] + box['width'] <= viewport['width'] and
                                            box['y'] + box['height'] <= viewport['height']
                                        )
                                        if debug:
                                            log_func(f"{selector['name']} button in viewport: {in_viewport}")
                                except Exception as e:
                                    if debug:
                                        log_func(f"Failed to get bounding box for {selector['name']} button: {str(e)}")
                                    in_viewport = False

                                is_enabled = await btn.is_enabled()
                                is_visible = await btn.is_visible()
                                if debug:
                                    log_func(f"{selector['name']} button - Visible: {is_visible}, Enabled: {is_enabled}")

                                # Proceed if enabled, even if not visible
                                if is_enabled:
                                    like_button = btn
                                    log_func(f"Found {selector['name']} button with aria-label '{aria_label}'")
                                    break
                                else:
                                    if debug:
                                        log_func(f"{selector['name']} button not enabled")
                        except Exception as e:
                            if debug:
                                log_func(f"Error evaluating {selector['name']} button: {str(e)}")
                            continue
                    if like_button:
                        break
                except Exception as e:
                    log_func(f"Failed to find {selector['name']} button in overlay for account {account_id}: {str(e)}")

            if not like_button:
                if debug:
                    overlay_aria_labels = await overlay.evaluate(
                        "(el) => Array.from(el.querySelectorAll('[aria-label]')).map(e => e.getAttribute('aria-label'))"
                    )
                    log_func(f"Overlay aria-labels: {overlay_aria_labels}")
                log_func(f"Could not find Like or React button in overlay for account {account_id}")
                if created_browser:
                    await browser.close()
                return False

            # Focus and click the button
            await like_button.focus()
            log_func(f"Focused {selector['name']} button for account {account_id}")

            await asyncio.sleep(random.uniform(1.0, 2.0))

            max_click_attempts = 3
            clicked = False
            for attempt in range(max_click_attempts):
                try:
                    # Method 1: Standard click
                    await like_button.click(timeout=5000)
                    log_func(f"Clicked {selector['name']} button for account {account_id} (standard click, attempt {attempt + 1})")
                    clicked = True
                    break
                except Exception as e:
                    log_func(f"Standard click failed for account {account_id} (attempt {attempt + 1}): {str(e)}")

                try:
                    # Method 2: JavaScript click
                    await like_button.evaluate("el => el.click()")
                    log_func(f"Clicked {selector['name']} button for account {account_id} (JavaScript click, attempt {attempt + 1})")
                    clicked = True
                    break
                except Exception as e:
                    log_func(f"JavaScript click failed for account {account_id} (attempt {attempt + 1}): {str(e)}")

                try:
                    # Method 3: Dispatch click event
                    await like_button.evaluate(
                        """el => {
                            const event = new MouseEvent('click', {bubbles: true, cancelable: true});
                            el.dispatchEvent(event);
                        }"""
                    )
                    log_func(f"Clicked {selector['name']} button for account {account_id} (dispatched click event, attempt {attempt + 1})")
                    clicked = True
                    break
                except Exception as e:
                    log_func(f"Dispatched click event failed for account {account_id} (attempt {attempt + 1}): {str(e)}")

                if attempt < max_click_attempts - 1:
                    await asyncio.sleep(2.0)

            if not clicked:
                if debug:
                    parent_html = await page.evaluate(
                        "(element) => element.parentElement.outerHTML", like_button
                    )
                    log_func(f"Parent HTML of {selector['name']} button: {parent_html}")
                log_func(f"All click attempts failed for {selector['name']} button for account {account_id}")
                if created_browser:
                    await browser.close()
                return False

            # Verify click
            await asyncio.sleep(2.0)
            try:
                is_liked = await like_button.evaluate("(el) => el.getAttribute('aria-label')?.includes('Unlike')")
                if is_liked:
                    log_func(f"Verified Like action successful for account {account_id}")
                else:
                    log_func(f"Like action may not have succeeded for account {account_id}")
            except Exception as e:
                log_func(f"Failed to verify Like action for account {account_id}: {str(e)}")

            if created_browser:
                await browser.close()
            return True

        except Exception as e:
            log_func(f"Error during Like action for account {account_id}: {str(e)}")
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