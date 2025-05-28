import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional

from app.models.playwright.actions.browser_utils import BrowserUtils
from app.models.playwright.base_action import AutomationAction
from app.utils.randomizer import Randomizer

from .base_selectors import FacebookSelectors
from .element_utils import ElementUtils


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
        self.element_utils = ElementUtils(log_func)

    @abstractmethod
    async def handle_share(self, page: Any, account_id: str) -> bool:
        """Handle the share operation for this post type."""
        pass

    async def _execute_share_flow(self, page: Any, account_id: str) -> bool:
        """Common share flow: find share button -> click -> find share now -> click."""
        # Step 1: Find and click the share button
        share_success = await self.element_utils.find_and_click_element(
            page, FacebookSelectors.SHARE_BUTTONS, account_id, "Share button"
        )

        if not share_success:
            self.log_func(f"Failed to click share button (account {account_id})")
            return False

        # Step 2: Wait for share dialog and click "Share now"
        await Randomizer.sleep(1.0, 2.0)

        share_now_success = await self.element_utils.find_and_click_element(
            page, FacebookSelectors.SHARE_NOW_BUTTONS, account_id, "Share now button"
        )

        if not share_now_success:
            self.log_func(f"Failed to click share now button (account {account_id})")
            return False

        # Step 3: Wait for completion
        await Randomizer.sleep(2.0, 4.0)
        return True


class NormalPostShareHandler(ShareHandler):
    """Handler for normal Facebook posts."""

    async def handle_share(self, page: Any, account_id: str) -> bool:
        """Handle sharing of normal posts."""
        self.log_func(f"Normal post share action for account {account_id}")

        # Try the improved JavaScript approach first
        success = await self._execute_share_js(page, account_id)
        if success:
            self.log_func(
                f"Share operation completed successfully for account {account_id}"
            )
            return True

        # Fallback to common flow
        self.log_func("Falling back to common share flow")
        return await self._execute_share_flow(page, account_id)

    async def _execute_share_js(self, page: Any, account_id: str) -> bool:
        """Execute JavaScript approach to share a post."""
        try:
            result = await page.evaluate("""() => {
                return new Promise((resolve) => {
                    // Find the visible post dialog
                    const postDialog = Array.from(document.querySelectorAll('div[role="dialog"][aria-labelledby]')).find(dlg => dlg.offsetParent !== null)
                    
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
                    }, 1000);
                });
            }""")

            self.log_func(f"JavaScript execution result: {result}")
            await Randomizer.sleep(3.0, 5.0)
            return result.get("success", False)

        except Exception as e:
            self.log_func(f"Error in JavaScript share execution: {str(e)}")
            return False


class VideoPostShareHandler(ShareHandler):
    """Handler for video posts."""

    async def handle_share(self, page: Any, account_id: str) -> bool:
        """Handle sharing of video posts."""
        self.log_func(f"Video post share action for account {account_id}")

        # Wait for page to stabilize
        await Randomizer.sleep(3.0, 5.0)

        # Use common share flow
        return await self._execute_share_flow(page, account_id)


class ReelPostShareHandler(ShareHandler):
    """Handler for reel posts."""

    async def handle_share(self, page: Any, account_id: str) -> bool:
        """Handle sharing of reel posts."""
        self.log_func(f"Reel post share action for account {account_id}")

        # Wait for page to stabilize
        await Randomizer.sleep(3.0, 5.0)

        # Use common share flow
        return await self._execute_share_flow(page, account_id)


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
        """Execute the share action on a Facebook post."""
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

            # Navigate to the post URL
            log_func(f"Navigating to URL: {share_request.url}")
            try:
                await page.goto(
                    share_request.url, wait_until="domcontentloaded", timeout=120000
                )
                await page.wait_for_load_state("networkidle", timeout=30000)
                log_func(f"Page loaded successfully for account {account_id}")
            except Exception as e:
                log_func(f"Navigation error (continuing anyway): {str(e)}")

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
