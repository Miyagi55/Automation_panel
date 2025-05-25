import re
from typing import Any, Callable, Dict, Optional

from app.models.playwright.actions.browser_utils import BrowserUtils
from app.models.playwright.base_action import AutomationAction
from app.utils.randomizer import Randomizer


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

        # Extract URL from the link field if it contains a URL within text TODO: make field validators for this instead
        extracted_url = self._extract_url(url)
        if extracted_url is not None:
            url = extracted_url
            log_func(f"Extracted URL from input: {url}")

        if not url:
            log_func(f"No URL provided for Share action on account {account_id}")
            return False

        if not url.startswith("http://") and not url.startswith("https://"):
            log_func(
                f"URL does not start with http:// or https:// for account {account_id}"
            )
            return False

        # case 1: normal post
        if "/share/p" in url:
            log_func(f"Normal post share action for account {account_id}")
            return await self._handle_normal_post(
                account_id, action_data, log_func, browser
            )

        # case 2: video post
        if "/share/v" in url:
            log_func(f"Video post share action for account {account_id}")
            return await self._handle_video_post(
                account_id, action_data, log_func, browser
            )

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

            # Implementing the more reliable approach based on the JS snippet
            log_func("Using improved dialog detection method")

            # Execute the JS to find and interact with the share dialog
            success = await self._execute_share_js(page, log_func)

            if success:
                log_func(
                    f"Share operation completed successfully for account {account_id}"
                )
                return True
            else:
                # Fallback to the original method if JS approach fails
                log_func("Falling back to original method")
                return await self._legacy_share_method(page, account_id, log_func)

        except Exception as e:
            log_func(f"Error during Share action: {str(e)}")
            return False
        finally:
            await browser_utils.cleanup_browser(created_browser, browser, playwright)

    async def _execute_share_js(
        self, page: Any, log_func: Callable[[str], None]
    ) -> bool:
        """Execute improved JavaScript approach to share a post."""
        try:
            # Run the JavaScript to find the dialog and share buttons
            result = await page.evaluate("""() => {
                return new Promise((resolve) => {
                    // Find the visible post dialog
                    const postDialog = Array.from(
                        document.querySelectorAll('div[role="dialog"][aria-labelledby]')
                    ).find(dlg => dlg.offsetParent !== null);
                    
                    if (!postDialog) {
                        console.warn('❌ No post dialog found');
                        resolve({success: false, error: 'No post dialog found'});
                        return;
                    }
                    
                    // Find the share button in the dialog
                    const openBtn = postDialog.querySelector(
                        '[role="button"][aria-label^="Send this to"],' +
                        '[role="button"][aria-label^="Envía esto a"]'
                    );
                    
                    if (!openBtn) {
                        console.warn('❌ Share button not found in dialog');
                        resolve({success: false, error: 'Share button not found in dialog'});
                        return;
                    }
                    
                    // Click the button to open the share dialog
                    openBtn.dispatchEvent(new MouseEvent('click', {
                        bubbles: true,
                        cancelable: true,
                        view: window
                    }));
                    
                    // Wait for the Share Now button to appear and click it
                    setTimeout(() => {
                        const shareNowBtn = document.querySelector(
                            'div[role="button"][aria-label="Share now"], ' +
                            'div[role="button"][aria-label="Compartir ahora"]'
                        );
                        
                        if (shareNowBtn) {
                            shareNowBtn.dispatchEvent(new MouseEvent('click', {
                                bubbles: true,
                                cancelable: true,
                                view: window
                            }));
                            
                            setTimeout(() => {
                                resolve({success: true});
                            }, 1000);
                        } else {
                            console.warn('❌ Share Now button not found');
                            resolve({success: false, error: 'Share Now button not found'});
                        }
                    }, 1000); // Wait 1 second for dialog to appear
                });
            }""")

            log_func(f"JavaScript execution result: {result}")

            # Wait a bit for the share action to complete
            await Randomizer.sleep(3.0, 5.0)

            return result.get("success", False)

        except Exception as e:
            log_func(f"Error in JavaScript share execution: {str(e)}")
            return False

    async def _legacy_share_method(
        self, page: Any, account_id: str, log_func: Callable[[str], None]
    ) -> bool:
        """Legacy method for sharing posts as fallback."""
        try:
            # Log all dialogs to help with debugging
            await self._log_visible_dialogs(page, log_func)

            # 1) Find and click the share button to open dialog
            share_selector = (
                'div[role="button"][aria-label="Send this to friends or post it on your profile."], '
                'div[role="button"][aria-label="Envía esto a tus amigos o publícalo en tu perfil."]'
            )
            log_func(f"Looking for share button with selector: {share_selector}")

            # First look for the button in visible dialog if present
            share_btn = await self._find_button_in_visible_dialog(
                page,
                '[role="button"][aria-label^="Send this to friends"], [role="button"][aria-label^="Envía esto a tus amigos"]',
                log_func,
            )

            # If not found in a dialog, try the main page
            if not share_btn:
                log_func("Share button not found in visible dialogs, trying main page")
                share_btn = await self._find_element(page, share_selector, log_func)

            if share_btn:
                log_func(f"Found share button for account {account_id}")

                # Check if button is visible and enabled
                is_visible = await self._is_element_visible(share_btn)
                is_enabled = await share_btn.is_enabled()

                if not is_visible or not is_enabled:
                    log_func(
                        f"Share button found but not interactive: visible={is_visible}, enabled={is_enabled}"
                    )
                    return False

                # Click the share button to open the dialog
                await self._click_element(
                    page, share_btn, "Share dialog button", log_func
                )
                log_func(f"Clicked share dialog button for account {account_id}")

                # Wait for dialog to appear and check if it's present
                await Randomizer.sleep(1.0, 2.5)

                # Log all dialogs after clicking to see what appeared
                await self._log_visible_dialogs(page, log_func)

                # Define the 'Share now' selector for dialog
                share_now_selector = (
                    'div[role="button"][aria-label="Share now"], '
                    'div[role="button"][aria-label="Compartir ahora"]'
                )

                # Try multiple times with increasing wait times to find the Share now button
                share_now_btn = await self._find_button_in_visible_dialog(
                    page,
                    '[role="button"][aria-label="Share now"], [role="button"][aria-label="Compartir ahora"]',
                    log_func,
                )

                if not share_now_btn:
                    log_func(
                        "Share now button not found in visible dialogs, trying with standard selector"
                    )
                    # Try using the standard approach as fallback
                    max_attempts = 5
                    for attempt in range(max_attempts):
                        share_now_btn = await page.query_selector(share_now_selector)
                        if share_now_btn and await self._is_element_visible(
                            share_now_btn
                        ):
                            break
                        log_func(
                            f"'Share now' button not found on attempt {attempt+1}, waiting..."
                        )
                        await Randomizer.sleep(1.0 * (attempt + 1), 1.5 * (attempt + 1))
                        # Try logging dialogs again to see any changes
                        if attempt == 2:  # Log on middle attempt
                            await self._log_visible_dialogs(page, log_func)

                if share_now_btn and await self._is_element_visible(share_now_btn):
                    # Verify button is interactive
                    is_enabled = await share_now_btn.is_enabled()
                    if not is_enabled:
                        log_func("Share now button found but not enabled")
                        return False

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
                        f"'Share now' button not found or not visible for account {account_id}"
                    )
                    return False
            else:
                log_func(f"Share dialog button not found for account {account_id}")
                return False
        except Exception as e:
            log_func(f"Error during legacy share method: {str(e)}")
            return False

    async def _log_visible_dialogs(
        self, page: Any, log_func: Callable[[str], None]
    ) -> None:
        """Log information about visible dialogs on the page."""
        try:
            dialog_info = await page.evaluate("""
                () => {
                    const dialogs = Array.from(document.querySelectorAll('div[role="dialog"]'));
                    return dialogs.map((dlg, i) => ({
                        index: i,
                        visible: dlg.offsetParent !== null,
                        ariaLabelledBy: dlg.getAttribute('aria-labelledby'),
                        ariaLabel: dlg.getAttribute('aria-label'),
                        buttons: Array.from(dlg.querySelectorAll('[role="button"][aria-label]'))
                            .filter(btn => btn.offsetParent !== null)
                            .map(btn => btn.getAttribute('aria-label'))
                    }));
                }
            """)
            log_func(f"Found {len(dialog_info)} dialogs on page")
            for dlg in dialog_info:
                log_func(
                    f"Dialog #{dlg['index']}: visible={dlg['visible']}, labelledBy={dlg['ariaLabelledBy']}, "
                    + f"label={dlg['ariaLabel']}, visible buttons: {dlg['buttons']}"
                )
        except Exception as e:
            log_func(f"Error logging dialogs: {str(e)}")

    async def _find_button_in_visible_dialog(
        self, page: Any, button_selector: str, log_func: Callable[[str], None]
    ) -> Optional[Any]:
        """Find a button within a visible dialog."""
        try:
            return await page.evaluate_handle(f"""
                () => {{
                    const dialogs = Array.from(document.querySelectorAll('div[role="dialog"][aria-labelledby]'));
                    for (const dlg of dialogs) {{
                        if (dlg.offsetParent === null) continue;  // ignore hidden dialogs
                        const btn = dlg.querySelector('{button_selector}');
                        if (btn) return btn;
                    }}
                    return null;
                }}
            """)
        except Exception as e:
            log_func(f"Error finding button in dialog: {str(e)}")
            return None

    async def _is_element_visible(self, element: Any) -> bool:
        """Check if an element is visible on the page."""
        try:
            is_visible = await element.is_visible()
            if not is_visible:
                return False

            # Additional check for actual visibility in DOM
            is_js_visible = await element.evaluate("""
                el => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    return rect.width > 0 && 
                           rect.height > 0 && 
                           style.display !== 'none' && 
                           style.visibility !== 'hidden' &&
                           el.offsetParent !== null;
                }
            """)
            return is_js_visible
        except:
            return False

    def _extract_url(self, text: str) -> Optional[str]:
        """Extract a URL from text if present."""
        # Extract full URL including path until whitespace or closing quote
        url_pattern = r"https?://[^\s\"']+"
        match = re.search(url_pattern, text)
        if match is not None:
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
            if aria_label is not None:
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
        if element is None:
            log_func(f"Cannot click null {element_name}")
            return False

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
