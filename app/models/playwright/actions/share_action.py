import re
from typing import Any, Callable, Dict, Optional

from app.models.playwright.actions.browser_utils import BrowserUtils
from app.utils.randomizer import Randomizer

from ..base_action import AutomationAction


class ShareAction(AutomationAction):
    """Automation action for sharing Facebook posts."""

    def __init__(self):
        super().__init__("Shares")

    async def execute(
        self,
        account_id: str,
        account_data: Dict[str, Any],
        action_data: Dict[str, Any],
        log_func: Callable[[str], None],
        browser: Optional[Any] = None,
    ) -> bool:
        """
        Execute the share action on a Facebook post.
        """
        url = action_data.get("link", "")
        debug = action_data.get("debug", True)

        # Extract URL from the link field if it contains a URL within text
        extracted_url = self._extract_url(url)
        if extracted_url:
            url = extracted_url
            log_func(f"Extracted URL from input: {url}")

        if not url or not url.startswith(("http://", "https://")):
            log_func(f"No valid URL provided for Share action on account {account_id}")
            return False

        browser_utils = BrowserUtils(account_id, log_func)
        user_data_dir = browser_utils.get_session_dir()
        log_func(f"Starting Share action for account {account_id}")

        created_browser, playwright, browser = await browser_utils.initialize_browser(
            browser, user_data_dir
        )
        try:
            page = await browser.new_page()

            # Navigate to the post URL with increased timeout
            log_func(f"Navigating to URL: {url}")
            try:
                # Use domcontentloaded instead of load for faster navigation
                await page.goto(url, wait_until="domcontentloaded", timeout=120000)
                # Wait for network to be mostly idle
                await page.wait_for_load_state("networkidle", timeout=30000)
                log_func(f"Page loaded successfully for account {account_id}")
            except Exception as e:
                log_func(f"Navigation error (continuing anyway): {str(e)}")
                # Try to continue even if there was a navigation error

            await Randomizer.sleep(3.0, 5.0)

            # 1) Find and click the share button to open dialog
            share_selector = 'div[role="button"][aria-label="Send this to friends or post it on your profile."]'
            log_func(f"Looking for share button with selector: {share_selector}")

            # Try multiple methods to find the share button
            share_btn = await self._find_element(page, share_selector, log_func)

            if share_btn:
                log_func(f"Found share button for account {account_id}")

                # Click the share button to open the dialog
                await self._click_element(
                    page, share_btn, "Share dialog button", log_func
                )
                log_func(f"Clicked share dialog button for account {account_id}")

                # Define the 'Share now' selector for dialog
                share_now_selector = 'div[role="button"][aria-label="Share now"]'

                # Wait for dialog to render and appear
                await Randomizer.sleep(1.0, 2.5)
                try:
                    await page.wait_for_selector(share_now_selector, timeout=10000)
                    log_func("Share dialog fully rendered")
                except Exception as e:
                    log_func(f"Share dialog did not render in time: {str(e)}")

                # 2) Find and click the "Share now" button in the dialog
                log_func(
                    f"Looking for 'Share now' button with selector: {share_now_selector}"
                )

                # Try multiple times with increasing wait times to find the Share now button
                share_now_btn = None
                max_attempts = 5
                for attempt in range(max_attempts):
                    share_now_btn = await page.query_selector(share_now_selector)
                    if share_now_btn:
                        break
                    log_func(
                        f"'Share now' button not found on attempt {attempt+1}, waiting..."
                    )
                    await Randomizer.sleep(1.0 * (attempt + 1), 1.5 * (attempt + 1))

                if share_now_btn:
                    # Click the "Share now" button
                    await self._click_element(
                        page, share_now_btn, "Share now button", log_func
                    )
                    log_func(f"Clicked 'Share now' button for account {account_id}")

                    # Wait for share confirmation
                    await Randomizer.sleep(2.0, 4.0)

                    # Verify the share was successful (look for success indicators)
                    # We don't use a complex selector here to avoid syntax issues
                    success_text = await page.evaluate("() => document.body.innerText")
                    if "shared" in success_text.lower():
                        log_func(f"Share confirmed successful for account {account_id}")
                    else:
                        log_func(
                            f"Share likely completed but couldn't confirm for account {account_id}"
                        )

                    return True
                else:
                    log_func(
                        f"'Share now' button not found after {max_attempts} attempts for account {account_id}"
                    )
                    return False
            else:
                log_func(f"Share dialog button not found for account {account_id}")
                return False
        except Exception as e:
            log_func(f"Error during Share action: {str(e)}")
            return False
        finally:
            await browser_utils.cleanup_browser(created_browser, browser, playwright)

    def _extract_url(self, text: str) -> Optional[str]:
        """Extract a URL from text if present."""
        # Simple URL pattern matching
        url_pattern = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+"
        match = re.search(url_pattern, text)
        if match:
            return match.group(0)
        return None

    async def _find_element(
        self, page: Any, selector: str, log_func: Callable[[str], None]
    ) -> Optional[Any]:
        """Find an element using multiple strategies."""
        # First try direct selector
        element = await page.query_selector(selector)
        if element:
            return element

        # If not found, scroll down a bit and try again
        await page.evaluate("window.scrollBy(0, 300)")
        await Randomizer.sleep(0.5, 1.0)
        element = await page.query_selector(selector)
        if element:
            return element

        # Try a more general approach if specific selector failed
        if "aria-label" in selector:
            # Extract the aria-label value
            aria_label = re.search(r'aria-label="([^"]+)"', selector)
            if aria_label:
                label_text = aria_label.group(1)
                log_func(
                    f"Trying to find element with aria-label containing: {label_text}"
                )
                # Look for elements with aria-label containing the text
                elements = await page.query_selector_all("[aria-label]")
                for el in elements:
                    attr = await el.get_attribute("aria-label")
                    if attr and label_text.lower() in attr.lower():
                        log_func(f"Found element with matching aria-label: {attr}")
                        return el

        return None

    async def _click_element(
        self,
        page: Any,
        element: Any,
        element_name: str,
        log_func: Callable[[str], None],
    ) -> bool:
        """Try multiple methods to click an element."""
        methods = [
            # Method 1: Standard Playwright click
            lambda: element.click(),
            # Method 2: JavaScript click
            lambda: page.evaluate("(el) => el.click()", element),
            # Method 3: MouseEvent dispatch as in the JS sample
            lambda: page.evaluate(
                'el => el.dispatchEvent(new MouseEvent("click", {bubbles: true, cancelable: true, view: window}))',
                element,
            ),
        ]

        for i, method in enumerate(methods):
            try:
                # method() returns a coroutine, so await it
                await method()
                log_func(f"Successfully clicked {element_name} using method {i+1}")
                return True
            except Exception as e:
                log_func(f"Click method {i+1} failed for {element_name}: {str(e)}")
                if i < len(methods) - 1:
                    log_func(f"Trying next click method for {element_name}")
                    await Randomizer.sleep(0.2, 0.5)

        log_func(f"All click methods failed for {element_name}")
        return False
