"""
Common element interaction utilities for Facebook automation actions.
Provides reusable methods for finding, clicking, and interacting with elements.
"""

import asyncio
from typing import Any, Callable, Optional

from app.utils.randomizer import Randomizer

from .base_selectors import FacebookSelectors, SelectorGroup


class ElementFinder:
    """Handles finding elements with retry logic and multiple selector strategies."""

    def __init__(self, log_func: Callable[[str], None]):
        self.log_func = log_func

    async def find_element_by_selector_group(
        self,
        context: Any,
        selector_group: SelectorGroup,
        timeout: int = 10000,
        max_attempts: int = 3,
        account_id: str = "",
    ) -> Optional[Any]:
        """Find element using a selector group with retry logic."""
        for attempt in range(max_attempts):
            for selector in selector_group.all_selectors:
                try:
                    self.log_func(
                        f"Attempt {attempt + 1}: Trying selector '{selector}' for {selector_group.description} (account {account_id})"
                    )
                    element = await context.wait_for_selector(selector, timeout=timeout)
                    if element and await self._is_element_interactable(element):
                        self.log_func(
                            f"Found interactable element with selector '{selector}' (account {account_id})"
                        )
                        return element
                    elif element:
                        self.log_func(
                            f"Element found but not interactable with selector '{selector}' (account {account_id})"
                        )
                except Exception as e:
                    self.log_func(
                        f"Selector '{selector}' failed on attempt {attempt + 1}: {str(e)} (account {account_id})"
                    )

            if attempt < max_attempts - 1:
                await Randomizer.sleep(1.0, 2.0)

        self.log_func(
            f"No interactable element found for {selector_group.description} after {max_attempts} attempts (account {account_id})"
        )
        return None

    async def find_visible_dialog(
        self, page: Any, account_id: str = "", timeout: int = 5000
    ) -> Optional[Any]:
        """Find a visible dialog/overlay on the page."""
        try:
            dialogs = await page.query_selector_all(
                FacebookSelectors.get_combined_selector(FacebookSelectors.DIALOGS)
            )
            for dialog in dialogs:
                if await self._is_element_visible(dialog):
                    self.log_func(f"Found visible dialog (account {account_id})")
                    return dialog
            self.log_func(f"No visible dialogs found (account {account_id})")
            return None
        except Exception as e:
            self.log_func(
                f"Error finding visible dialog: {str(e)} (account {account_id})"
            )
            return None

    async def _is_element_interactable(self, element: Any) -> bool:
        """Check if element is both visible and enabled."""
        try:
            # Use simpler visibility check like the old working like action
            is_visible = await element.is_visible()
            is_enabled = await element.is_enabled()

            # If basic checks pass, it's likely interactable
            if is_visible and is_enabled:
                return True

            # Fallback: if basic visibility fails, try JavaScript check
            # but be more lenient than before
            if is_enabled:
                try:
                    is_js_visible = await element.evaluate("""
                        el => {
                            const rect = el.getBoundingClientRect();
                            return rect.width > 0 && rect.height > 0;
                        }
                    """)
                    return is_js_visible
                except:
                    # If JS check fails, still consider it interactable if enabled
                    return True

            return False
        except:
            return False

    async def _is_element_visible(self, element: Any) -> bool:
        """Check if element is visible using multiple methods."""
        try:
            # Playwright's built-in visibility check
            is_visible = await element.is_visible()
            if not is_visible:
                return False

            # Additional JavaScript visibility check
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


class ElementClicker:
    """Handles clicking elements with multiple fallback strategies."""

    def __init__(self, log_func: Callable[[str], None]):
        self.log_func = log_func

    async def click_element(
        self,
        element: Any,
        element_name: str,
        account_id: str = "",
        max_attempts: int = 3,
    ) -> bool:
        """Click element using multiple methods with retry logic."""
        if not element:
            self.log_func(f"Cannot click null {element_name} (account {account_id})")
            return False

        # Ensure element is in viewport
        await self._ensure_element_in_viewport(element, element_name, account_id)

        # Focus the element like the old working like action
        try:
            await element.focus()
            self.log_func(f"Focused {element_name} (account {account_id})")
        except Exception as e:
            self.log_func(
                f"Could not focus {element_name}: {str(e)} (account {account_id})"
            )

        click_methods = [
            (lambda: element.click(timeout=10000), "standard click"),
            (lambda: element.evaluate("el => el.click()"), "JavaScript click"),
            (
                lambda: element.evaluate(
                    """el => {
                        const event = new MouseEvent('click', {
                            bubbles: true, 
                            cancelable: true, 
                            view: window
                        });
                        el.dispatchEvent(event);
                    }"""
                ),
                "dispatched click event",
            ),
        ]

        for attempt in range(max_attempts):
            for click_fn, method_name in click_methods:
                try:
                    await click_fn()
                    self.log_func(
                        f"Successfully clicked {element_name} using {method_name} (attempt {attempt + 1}) (account {account_id})"
                    )
                    await Randomizer.sleep(0.5, 1.5)  # Wait for action to register
                    return True
                except Exception as e:
                    self.log_func(
                        f"{method_name.capitalize()} failed for {element_name} (attempt {attempt + 1}): {str(e)} (account {account_id})"
                    )

            if attempt < max_attempts - 1:
                await Randomizer.sleep(0.5, 1.0)

        self.log_func(
            f"All click methods failed for {element_name} (account {account_id})"
        )
        return False

    async def _ensure_element_in_viewport(
        self, element: Any, element_name: str, account_id: str
    ) -> None:
        """Scroll element into viewport."""
        try:
            await element.evaluate(
                "el => el.scrollIntoView({block: 'center', inline: 'center', behavior: 'smooth'})"
            )
            await Randomizer.sleep(0.5, 1.0)
        except Exception as e:
            self.log_func(
                f"Failed to scroll {element_name} into viewport: {str(e)} (account {account_id})"
            )


class ElementWaiter:
    """Handles waiting for elements and page states."""

    def __init__(self, log_func: Callable[[str], None]):
        self.log_func = log_func

    async def wait_for_overlay_with_element(
        self,
        page: Any,
        target_selector_group: SelectorGroup,
        account_id: str = "",
        max_attempts: int = 4,
        wait_between_attempts: float = 3.0,
    ) -> Optional[Any]:
        """Wait for an overlay that contains a specific element."""
        self.log_func(
            f"Waiting for overlay with {target_selector_group.description} (account {account_id})"
        )

        for attempt in range(max_attempts):
            try:
                # Wait for any dialog to appear
                overlay = await page.wait_for_selector(
                    FacebookSelectors.get_combined_selector(FacebookSelectors.DIALOGS),
                    timeout=7000,
                )

                if overlay:
                    # Check if the overlay contains the target element
                    target_element = await overlay.query_selector(
                        FacebookSelectors.get_combined_selector(target_selector_group)
                    )
                    if target_element:
                        self.log_func(
                            f"Overlay with {target_selector_group.description} found on attempt {attempt + 1} (account {account_id})"
                        )
                        return overlay

                self.log_func(
                    f"Overlay found but no {target_selector_group.description} on attempt {attempt + 1} (account {account_id})"
                )

            except Exception:
                self.log_func(
                    f"No overlay detected on attempt {attempt + 1} (account {account_id})"
                )

            if attempt < max_attempts - 1:
                await asyncio.sleep(wait_between_attempts)

        self.log_func(
            f"No overlay with {target_selector_group.description} found after {max_attempts} attempts (account {account_id})"
        )
        return None

    async def wait_for_page_load(
        self, page: Any, account_id: str = "", timeout: int = 60000
    ) -> bool:
        """Wait for page to load completely."""
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
            self.log_func(f"Page loaded successfully (account {account_id})")
            return True
        except Exception as e:
            self.log_func(
                f"Page load timeout or error: {str(e)} (account {account_id})"
            )
            return False


class PostTypeDetector:
    """Detects Facebook post types (normal, video, live, reel)."""

    def __init__(self, log_func: Callable[[str], None]):
        self.log_func = log_func

    async def detect_post_type(self, page: Any, account_id: str = "") -> str:
        """Detect the type of Facebook post."""
        try:
            # Check for video
            video_element = await page.query_selector(
                FacebookSelectors.get_combined_selector(
                    FacebookSelectors.VIDEO_INDICATORS
                )
            )
            if video_element:
                self.log_func(f"Detected video post (account {account_id})")
                return "video"

            # Check for live indicators
            live_element = await page.query_selector(
                FacebookSelectors.get_combined_selector(
                    FacebookSelectors.LIVE_INDICATORS
                )
            )
            if live_element:
                self.log_func(f"Detected live post (account {account_id})")
                return "live"

            self.log_func(f"Detected normal post (account {account_id})")
            return "normal"

        except Exception as e:
            self.log_func(f"Error detecting post type: {str(e)} (account {account_id})")
            return "normal"  # Fallback to normal post


class ElementUtils:
    """Main utility class that combines all element interaction capabilities."""

    def __init__(self, log_func: Callable[[str], None]):
        self.log_func = log_func
        self.finder = ElementFinder(log_func)
        self.clicker = ElementClicker(log_func)
        self.waiter = ElementWaiter(log_func)
        self.detector = PostTypeDetector(log_func)

    async def find_and_click_element(
        self,
        context: Any,
        selector_group: SelectorGroup,
        account_id: str = "",
        element_name: str = None,
    ) -> bool:
        """Find and click an element in one operation."""
        element_name = element_name or selector_group.description
        element = await self.finder.find_element_by_selector_group(
            context, selector_group, account_id=account_id
        )
        if not element:
            return False

        return await self.clicker.click_element(element, element_name, account_id)

    async def scroll_and_find_element(
        self,
        page: Any,
        selector_group: SelectorGroup,
        scroll_distance: int = 300,
        account_id: str = "",
    ) -> Optional[Any]:
        """Scroll page and then find element."""
        await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
        await Randomizer.sleep(0.5, 1.0)
        return await self.finder.find_element_by_selector_group(
            page, selector_group, account_id=account_id
        )
