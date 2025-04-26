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
        debug = action_data.get("debug", False)
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
            try:
                await page.goto(url, wait_until="load", timeout=60000)
                page_title = await page.title()
                page_url = page.url
               
            except Exception as e:
                log_func(f"Navigation failed for account {account_id}: {str(e)}")
                return False

            log_func(f"Waiting for post overlay to load for account {account_id}")
            overlay = None
            for attempt in range(3):
                try:
                    overlay = await page.wait_for_selector(
                        'div[role="dialog"]:has([aria-label="Like"]), div[role="dialog"]:has([aria-label="React"])',
                        timeout=2500
                    )
                    if overlay:
                        break
                    log_func(f"Overlay not found on attempt {attempt + 1}/3 for account {account_id}")
                    await asyncio.sleep(2.0)
                except Exception as e:
                    log_func(f"Overlay wait failed on attempt {attempt + 1}/3 for account {account_id}: {str(e)}")
                    await asyncio.sleep(2.0)

            if not overlay:
                if debug:
                    log_func(f"No post overlay found for account {account_id}")
                log_func(f"Could not find Like button in overlay for account {account_id}")
                if created_browser:
                    await browser.close()
                return False

            await asyncio.sleep(3.0)
            log_func(f"Post overlay loaded for account {account_id}")

            await page.evaluate("window.scrollBy(0, 280)")
            await asyncio.sleep(2.0)

            like_button = None
            selector = {"type": "aria-label", "value": r"^(Like|Me gusta)$", "scope": "overlay"}

            try:
                await asyncio.sleep(2.0)
                buttons = await overlay.query_selector_all("[aria-label]")

                for btn in buttons:
                    try:
                        aria_label = await btn.evaluate("""(el) => el.getAttribute('aria-label')""")
                        if debug:
                            button_html = await btn.evaluate("""(el) => el.outerHTML""")
                            log_func(
                                f"Evaluating button with aria-label: '{aria_label}' in overlay scope, HTML: {button_html[:100]}..."
                            )
                        if aria_label and re.match(selector["value"], aria_label):
                            for attempt in range(5):
                                if await btn.is_visible():
                                    like_button = btn
                                    log_func(f"Found like button with aria-label '{aria_label}' in overlay scope")
                                    break
                                if debug:
                                    log_func(
                                        f"Button with aria-label '{aria_label}' not visible in overlay scope, retry {attempt + 1}/5"
                                    )
                                await asyncio.sleep(1.5)
                            if like_button:
                                break
                            if debug:
                                log_func(f"Button with aria-label '{aria_label}' failed visibility check in overlay scope")
                    except Exception as e:
                        if debug:
                            log_func(f"Error evaluating button in overlay scope: {str(e)}")
                        continue
            except Exception as e:
                log_func(f"Failed to find like button in overlay scope for account {account_id}: {str(e)}")

            if not like_button:
                if debug:
                    overlay_aria_labels = await overlay.evaluate(
                        """(el) => Array.from(el.querySelectorAll('[aria-label]')).map(e => e.getAttribute('aria-label'))"""
                    )
                    log_func(f"Overlay aria-labels: {overlay_aria_labels}")
                log_func(f"Could not find Like button in overlay for account {account_id}")
                if created_browser:
                    await browser.close()
                return False

            await like_button.focus()
            log_func(f"Focused like button for account {account_id}")

            await asyncio.sleep(random.uniform(2.0, 4.0))

            max_click_attempts = 3
            for attempt in range(max_click_attempts):
                try:
                    await like_button.click()
                    log_func(f"Clicked like button for account {account_id} (attempt {attempt + 1})")
                    break
                except Exception as e:
                    log_func(f"Standard click failed for account {account_id} (attempt {attempt + 1}): {str(e)}")
                    if attempt < max_click_attempts - 1:
                        await asyncio.sleep(2.0)
                        continue
                    parent_html = await page.evaluate(
                        "(element) => element.parentElement.outerHTML", like_button
                    )
                    log_func(f"Parent HTML of like button: {parent_html}")
                    await page.evaluate("(element) => element.click()", like_button)
                    log_func(f"Clicked like button using JavaScript for account {account_id}")

            await asyncio.sleep(3)

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