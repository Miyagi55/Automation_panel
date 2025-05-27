import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional

from app.models.playwright.actions.browser_utils import BrowserUtils
from app.models.playwright.base_action import AutomationAction
from app.utils.randomizer import Randomizer


class PostType(Enum):
    """Enumeration of supported Facebook post types."""

    NORMAL = "normal"  # eg: https://www.facebook.com/share/p/1234567890 pattern: "/p/"
    VIDEO = "video"  # eg: https://www.facebook.com/share/v/1G9GWrjMZb/ pattern: "/v/"
    REEL = "reel"  # eg: https://www.facebook.com/share/r/16HzqZ3SKQ/ pattern: "/r/"
    LIVE = "live"  # eg: https://www.facebook.com/share/v/16WuKb9k51/ pattern: "/v/" (ignored for now)


@dataclass
class ShareRequest:
    """Data class for validated share request parameters."""

    url: str
    post_type: PostType
    debug: bool = True


class URLValidator:
    """Validates and extracts information from Facebook URLs."""

    # URL patterns for different post types
    URL_PATTERNS = {
        PostType.NORMAL: r"/share/p/",
        PostType.VIDEO: r"/share/v/",
        PostType.REEL: r"/share/r/",
        PostType.LIVE: r"/share/v/",  # Same pattern as video, handled separately
    }

    @classmethod
    def validate_and_extract(cls, raw_url: str) -> Optional[ShareRequest]:
        """
        Validate URL and extract post type information.

        Args:
            raw_url: Raw URL input that may contain extra text

        Returns:
            ShareRequest object if valid, None otherwise
        """
        # Extract URL from text if needed
        extracted_url = cls._extract_url_from_text(raw_url)
        if not extracted_url:
            return None

        # Validate URL format
        if not cls._is_valid_url_format(extracted_url):
            return None

        # Determine post type
        post_type = cls._determine_post_type(extracted_url)
        if not post_type:
            return None

        return ShareRequest(url=extracted_url, post_type=post_type, debug=True)

    @classmethod
    def _extract_url_from_text(cls, text: str) -> Optional[str]:
        """Extract a URL from text if present."""
        url_pattern = r"https?://[^\s\"']+"
        match = re.search(url_pattern, text)
        return match.group(0) if match else None

    @classmethod
    def _is_valid_url_format(cls, url: str) -> bool:
        """Check if URL has valid format."""
        return url.startswith(("http://", "https://"))

    @classmethod
    def _determine_post_type(cls, url: str) -> Optional[PostType]:
        """Determine the post type from URL pattern."""
        for post_type, pattern in cls.URL_PATTERNS.items():
            if re.search(pattern, url):
                # Special handling for live posts (ignore for now)
                if post_type == PostType.VIDEO and cls._is_live_post(url):
                    return PostType.LIVE
                return post_type
        return None

    @classmethod
    def _is_live_post(cls, url: str) -> bool:
        """Check if a video URL is actually a live post (placeholder logic)."""
        # TODO: Implement proper live post detection
        # For now, we'll assume all /share/v/ are regular videos
        return False


class ShareHandler(ABC):
    """Abstract base class for post type specific share handlers."""

    def __init__(self, log_func: Callable[[str], None]):
        self.log_func = log_func

    @abstractmethod
    async def handle_share(self, page: Any, account_id: str) -> bool:
        """Handle the share operation for this post type."""
        pass


class NormalPostShareHandler(ShareHandler):
    """Handler for normal Facebook posts (maintains existing logic)."""

    async def handle_share(self, page: Any, account_id: str) -> bool:
        """Handle sharing of normal posts using existing proven logic."""
        self.log_func(f"Normal post share action for account {account_id}")

        # Use the existing proven JavaScript approach first
        success = await self._execute_share_js(page)

        if success:
            self.log_func(
                f"Share operation completed successfully for account {account_id}"
            )
            return True
        else:
            # Fallback to the original method if JS approach fails
            self.log_func("Falling back to original method")
            return await self._legacy_share_method(page, account_id)

    async def _execute_share_js(self, page: Any) -> bool:
        """Execute improved JavaScript approach to share a post."""
        try:
            # Run the JavaScript to find the dialog and share buttons
            result = await page.evaluate("""() => {
                
                // This identifies the post dialog:
                
                return new Promise((resolve) => {
                    // Find the visible post dialog
                    const postDialog = Array.from(document.querySelectorAll('div[role="dialog"][aria-labelledby]')).find(dlg => dlg.offsetParent !== null)
                    
                    if (!postDialog) {
                        console.warn('❌ No post dialog found');
                        resolve({success: false, error: 'No post dialog found'});
                        return;
                    }
                    
                    // Find the share button in the dialog
                    // TODO: this is a common pattern for for the post dialog, should DRY.
                    // NOTE: selectors are truncated but functional:
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
                    
                    // Confirm button
                    // NOTE: this is a common pattern for share dialogs. ()
                    // TODO: for other posts beside normal posts, we need to find the correct button to click.
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

            self.log_func(f"JavaScript execution result: {result}")

            # Wait a bit for the share action to complete
            await Randomizer.sleep(3.0, 5.0)

            return result.get("success", False)

        except Exception as e:
            self.log_func(f"Error in JavaScript share execution: {str(e)}")
            return False

    async def _legacy_share_method(self, page: Any, account_id: str) -> bool:
        """Legacy method for sharing posts as fallback."""
        try:
            # Log all dialogs to help with debugging
            await self._log_visible_dialogs(page)

            # 1) Find and click the share button to open dialog
            SHARE_SELECTORS = (
                'div[role="button"][aria-label="Send this to friends or post it on your profile."], '
                'div[role="button"][aria-label="Envía esto a tus amigos o publícalo en tu perfil."]'
            )
            self.log_func(f"Looking for share button with selector: {SHARE_SELECTORS}")

            # First look for the button in visible dialog if present
            share_btn = await self._find_button_in_visible_dialog(
                page,
                '[role="button"][aria-label^="Send this to friends"], [role="button"][aria-label^="Envía esto a tus amigos"]',
            )

            # If not found in a dialog, try the main page
            if not share_btn:
                self.log_func(
                    "Share button not found in visible dialogs, trying main page"
                )
                share_btn = await self._find_element(page, SHARE_SELECTORS)

            if share_btn:
                self.log_func(f"Found share button for account {account_id}")

                # Check if button is visible and enabled
                is_visible = await self._is_element_visible(share_btn)
                is_enabled = await share_btn.is_enabled()

                if not is_visible or not is_enabled:
                    self.log_func(
                        f"Share button found but not interactive: visible={is_visible}, enabled={is_enabled}"
                    )
                    return False

                # Click the share button to open the dialog
                await self._click_element(page, share_btn, "Share dialog button")
                self.log_func(f"Clicked share dialog button for account {account_id}")

                # Wait for dialog to appear and check if it's present
                await Randomizer.sleep(1.0, 2.5)

                # Log all dialogs after clicking to see what appeared
                await self._log_visible_dialogs(page)

                # Define the 'Share now' selector for dialog (COMMON)
                # TODO: this ones common and should be reused.
                share_now_selector = (
                    'div[role="button"][aria-label="Share now"], '
                    'div[role="button"][aria-label="Compartir ahora"]'
                )

                # Try multiple times with increasing wait times to find the Share now button
                share_now_btn = await self._find_button_in_visible_dialog(
                    page,
                    '[role="button"][aria-label="Share now"], [role="button"][aria-label="Compartir ahora"]',
                )

                if not share_now_btn:
                    self.log_func(
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
                        self.log_func(
                            f"'Share now' button not found on attempt {attempt+1}, waiting..."
                        )
                        await Randomizer.sleep(1.0 * (attempt + 1), 1.5 * (attempt + 1))
                        # Try logging dialogs again to see any changes
                        if attempt == 2:  # Log on middle attempt
                            await self._log_visible_dialogs(page)

                if share_now_btn and await self._is_element_visible(share_now_btn):
                    # Verify button is interactive
                    is_enabled = await share_now_btn.is_enabled()
                    if not is_enabled:
                        self.log_func("Share now button found but not enabled")
                        return False

                    # Click the "Share now" button
                    await self._click_element(page, share_now_btn, "Share now button")
                    self.log_func(
                        f"Clicked 'Share now' button for account {account_id}"
                    )

                    # Wait for share confirmation
                    await Randomizer.sleep(2.0, 4.0)

                    # Verify the share was successful (look for success indicators)
                    # We don't use a complex selector here to avoid syntax issues
                    success_text = await page.evaluate("() => document.body.innerText")
                    if "shared" in success_text.lower():
                        self.log_func(
                            f"Share confirmed successful for account {account_id}"
                        )
                    else:
                        self.log_func(
                            f"Share likely completed but couldn't confirm for account {account_id}"
                        )

                    return True
                else:
                    self.log_func(
                        f"'Share now' button not found or not visible for account {account_id}"
                    )
                    return False
            else:
                self.log_func(f"Share dialog button not found for account {account_id}")
                return False
        except Exception as e:
            self.log_func(f"Error during legacy share method: {str(e)}")
            return False

    async def _log_visible_dialogs(self, page: Any) -> None:
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
            self.log_func(f"Found {len(dialog_info)} dialogs on page")
            for dlg in dialog_info:
                self.log_func(
                    f"Dialog #{dlg['index']}: visible={dlg['visible']}, labelledBy={dlg['ariaLabelledBy']}, "
                    + f"label={dlg['ariaLabel']}, visible buttons: {dlg['buttons']}"
                )
        except Exception as e:
            self.log_func(f"Error logging dialogs: {str(e)}")

    async def _find_button_in_visible_dialog(
        self, page: Any, button_selector: str
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
            self.log_func(f"Error finding button in dialog: {str(e)}")
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

    async def _find_element(self, page: Any, selector: str) -> Optional[Any]:
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
                self.log_func(
                    f"Trying to find element with aria-label containing: {label_text}"
                )
                # Look for elements with aria-label containing the text
                elements = await page.query_selector_all("[aria-label]")
                for el in elements:
                    attr = await el.get_attribute("aria-label")
                    if attr and label_text.lower() in attr.lower():
                        self.log_func(f"Found element with matching aria-label: {attr}")
                        return el

        return None

    async def _click_element(
        self,
        page: Any,
        element: Any,
        element_name: str,
    ) -> bool:
        """Try multiple methods to click an element."""
        if element is None:
            self.log_func(f"Cannot click null {element_name}")
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
                self.log_func(f"Successfully clicked {element_name} using method {i+1}")
                return True
            except Exception as e:
                self.log_func(f"Click method {i+1} failed for {element_name}: {str(e)}")
                if i < len(methods) - 1:
                    self.log_func(f"Trying next click method for {element_name}")
                    await Randomizer.sleep(0.2, 0.5)

        self.log_func(f"All click methods failed for {element_name}")
        return False


class VideoPostShareHandler(ShareHandler):
    """Handler for video posts."""

    async def handle_share(self, page: Any, account_id: str) -> bool:
        """Handle sharing of video posts."""
        self.log_func(f"Video post share action for account {account_id}")
        # TODO: Implement video-specific share logic
        self.log_func("Video post sharing not yet implemented")
        return False


class ReelPostShareHandler(ShareHandler):
    """Handler for reel posts."""

    async def handle_share(self, page: Any, account_id: str) -> bool:
        """Handle sharing of reel posts."""
        self.log_func(f"Reel post share action for account {account_id}")
        # TODO: Implement reel-specific share logic
        self.log_func("Reel post sharing not yet implemented")
        return False


class LivePostShareHandler(ShareHandler):
    """Handler for live posts."""

    async def handle_share(self, page: Any, account_id: str) -> bool:
        """Handle sharing of live posts."""
        self.log_func(f"Live post share action for account {account_id} (ignored)")
        # Live posts are ignored for now
        self.log_func("Live post sharing is ignored")
        return False


class ShareRouter:
    """Routes share requests to appropriate handlers based on post type."""

    def __init__(self, log_func: Callable[[str], None]):
        self.log_func = log_func
        self._handlers = {
            PostType.NORMAL: NormalPostShareHandler(log_func),
            PostType.VIDEO: VideoPostShareHandler(log_func),
            PostType.REEL: ReelPostShareHandler(log_func),
            PostType.LIVE: LivePostShareHandler(log_func),
        }

    async def route_share_request(
        self, share_request: ShareRequest, page: Any, account_id: str
    ) -> bool:
        """Route the share request to the appropriate handler."""
        handler = self._handlers.get(share_request.post_type)
        if not handler:
            self.log_func(f"No handler found for post type: {share_request.post_type}")
            return False

        return await handler.handle_share(page, account_id)


class ShareAction(AutomationAction):
    """Automation action for sharing Facebook posts with improved routing and validation."""

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
        raw_url = action_data.get("link", "")

        # Validate and extract share request information
        share_request = URLValidator.validate_and_extract(raw_url)
        if not share_request:
            log_func(
                f"Invalid or unsupported URL for Share action on account {account_id}: {raw_url}"
            )
            return False

        log_func(f"Extracted URL: {share_request.url}")
        log_func(f"Detected post type: {share_request.post_type.value}")

        browser_utils = BrowserUtils(account_id, log_func)
        user_data_dir = browser_utils.get_session_dir()
        log_func(f"Starting Share action for account {account_id}")

        created_browser, playwright, browser = await browser_utils.initialize_browser(
            browser, user_data_dir
        )
        try:
            page = await browser.new_page()

            # Navigate to the post URL with increased timeout
            log_func(f"Navigating to URL: {share_request.url}")
            try:
                # Use domcontentloaded instead of load for faster navigation
                await page.goto(
                    share_request.url, wait_until="domcontentloaded", timeout=120000
                )
                # Wait for network to be mostly idle
                await page.wait_for_load_state("networkidle", timeout=30000)
                log_func(f"Page loaded successfully for account {account_id}")
            except Exception as e:
                log_func(f"Navigation error (continuing anyway): {str(e)}")
                # Try to continue even if there was a navigation error

            await Randomizer.sleep(3.0, 5.0)

            # Route the share request to the appropriate handler
            router = ShareRouter(log_func)
            success = await router.route_share_request(share_request, page, account_id)

            if success:
                log_func(
                    f"Share operation completed successfully for account {account_id}"
                )
            else:
                log_func(f"Share operation failed for account {account_id}")

            return success

        except Exception as e:
            log_func(f"Error during Share action: {str(e)}")
            return False
        finally:
            await browser_utils.cleanup_browser(created_browser, browser, playwright)
