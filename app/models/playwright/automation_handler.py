"""
Automation handler for executing Facebook automation tasks.
"""

import asyncio
import random
import re
from typing import Any, Callable, Dict, Optional

from .browser_manager import BrowserManager
from .session_handler import SessionHandler






#-----------------------------class---------------------------------------------------------------#
class AutomationAction:
    """
    Base class for automation actions.
    All specific actions should inherit from this.
    """

    def __init__(self, name: str):
        self.name = name
        self.session_handler = SessionHandler()

    async def execute(
        self,
        account_id: str,
        account_data: Dict[str, Any],
        action_data: Dict[str, Any],
        log_func: Callable[[str], None],
        browser: Optional[Any] = None,
    ) -> bool:
        """Execute the automation action."""
        raise NotImplementedError("Subclasses must implement execute()")









#-----------------------------class---------------------------------------------------------------#
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
            # Import here to allow for lazy loading
            from patchright.async_api import async_playwright

            # Use existing browser context if provided and not closed
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
                log_func(f"Navigated to post URL for account {account_id}: {page_url}, Title: {page_title}")
            except Exception as e:
                log_func(f"Navigation failed for account {account_id}: {str(e)}")
                return False

            # Wait for post overlay with retry
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

            # Additional wait for components to render (e.g., images)
            await asyncio.sleep(3.0)
            log_func(f"Post overlay loaded for account {account_id}")

            # Scroll to ensure the post is in view
            await page.evaluate("window.scrollBy(0, 300)")
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

            # Focus the button to ensure it’s interactive
            await like_button.focus()
            log_func(f"Focused like button for account {account_id}")

            # Add a delay before clicking
            await asyncio.sleep(random.uniform(2.0, 4.0))

            # Attempt to click the like button with retries
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

            # Wait to ensure the like is registered
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







#-----------------------------class---------------------------------------------------------------#
class CommentAction(AutomationAction):
    """Automation action for commenting on Facebook posts."""

    def __init__(self):
        super().__init__("Comments")

    async def execute(
        self,
        account_id: str,
        account_data: Dict[str, Any],
        action_data: Dict[str, Any],
        log_func: Callable[[str], None],
        browser: Optional[Any] = None,
    ) -> bool:
        """Execute the comment action on a post."""
        url = action_data.get("link", "")
        comments_file = action_data.get("comments_file", None)

        if not url:
            log_func(f"No URL provided for Comment action on account {account_id}")
            return False

        # Load comments from file if provided
        comments = ["Great post!", "Nice!", "Thanks for sharing!"]  # Default comments
        if comments_file:
            try:
                with open(comments_file, "r") as f:
                    file_comments = [
                        line.strip() for line in f.readlines() if line.strip()
                    ]
                    if file_comments:
                        comments = file_comments
            except Exception as e:
                log_func(
                    f"Error loading comments file for account {account_id}: {str(e)}"
                )

        # Select a random comment
        comment_text = random.choice(comments)

        browser_manager = BrowserManager()
        chromium_exe = browser_manager.get_chromium_executable(log_func)
        if not chromium_exe:
            log_func(f"No chromium executable found for account {account_id}")
            return False

        user_data_dir = browser_manager.get_session_dir(account_id)
        log_func(f"Starting Comment action for account {account_id} on {url}")

        created_browser = False
        playwright = None
        try:
            # Import here to allow for lazy loading
            from patchright.async_api import async_playwright

            # Use existing browser context if provided and not closed
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
            await page.goto(url, wait_until="load", timeout=60000)
            log_func(f"Navigated to post URL in new tab for account {account_id}")

            # Wait for the comment field to load
            comment_selectors = [
                'div[aria-label="Write a comment"]',
                'div[data-testid="commentForm"]',
                'form[data-testid="UFI2ComposerForm"]',
            ]

            comment_field = None
            for selector in comment_selectors:
                try:
                    comment_field = await page.wait_for_selector(
                        selector, timeout=5000
                    )
                    if comment_field:
                        break
                except:
                    continue

            if not comment_field:
                log_func(f"Could not find comment field for account {account_id}")
                if created_browser:
                    await browser.close()
                return False

            # Click the comment field to focus it
            await comment_field.click()

            # Type the comment with human-like delays
            await self._type_with_human_delay(comment_field, comment_text, log_func)

            # Press Enter to submit the comment
            await page.keyboard.press("Enter")
            log_func(f"Posted comment for account {account_id}")

            # Wait to ensure the comment is posted
            await asyncio.sleep(5)

            if created_browser:
                await browser.close()
            return True

        except Exception as e:
            log_func(f"Error during Comment action for account {account_id}: {str(e)}")
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








#-----------------------------class---------------------------------------------------------------#
class AutomationHandler:
    """
    Manages and executes automation actions.
    """

    def __init__(self):
        self.actions = {
            "Likes": LikeAction(),
            "Comments": CommentAction(),
            # Add more actions as needed
        }
        self.session_handler = SessionHandler()
        self.playwright = None

    async def execute_workflow(
        self,
        workflow_name: str,
        workflow_data: Dict[str, Any],
        accounts: Dict[str, Dict[str, Any]],
        log_func: Callable[[str], None],
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> bool:
        """
        Execute a complete workflow with multiple actions on multiple accounts.
        """
        log_func(f"Starting workflow: {workflow_name}")

        # Get the actions and account emails from workflow data
        action_configs = workflow_data.get("actions", {})
        account_user = workflow_data.get("accounts", [])

        if not action_configs:
            log_func(f"No actions defined for workflow: {workflow_name}")
            return False

        if not account_user:
            log_func(f"No accounts selected for workflow: {workflow_name}")
            return False

        # Find account IDs from emails
        account_ids = []
        for account_id, account_data in accounts.items():
            if account_data.get("user") in account_user:
                account_ids.append(account_id)

        if not account_ids:
            log_func(f"Could not find any valid accounts for workflow: {workflow_name}")
            return False

        log_func(
            f"Executing workflow {workflow_name} on {len(account_ids)} accounts with {len(action_configs)} actions"
        )

        total_operations = len(account_ids) * len(action_configs)
        completed_operations = 0

        try:
            # Execute each action on each account
            for account_id in account_ids:
                account_data = accounts[account_id]

                # Check if the account is logged in without forcing login
                result = await self.session_handler.open_sessions(
                    account_id, log_func, keep_browser_open_seconds=0, skip_simulation=True
                )
                log_func(f"Session result for account {account_id}: {result}")
                is_logged_in, sim_success = result.get(account_id, (False, False))

                # Retrieve browser context from BatchProcessor
                browser = self.session_handler.batch_processor.get_browser_context(account_id)
                if not browser:
                    log_func(f"No browser context available for account {account_id}")
                    is_logged_in = False

                if not is_logged_in:
                    log_func(f"Error: Account {account_id} is not logged in, skipping actions")
                    if browser and not (hasattr(browser, '_closed') and browser._closed):
                        try:
                            await browser.close()
                            log_func(f"Closed browser for account {account_id}")
                        except Exception as e:
                            log_func(f"Error closing browser for account {account_id}: {str(e)}")
                    completed_operations += len(action_configs)
                    if progress_callback:
                        progress_callback(completed_operations / total_operations)
                    continue

                # Execute each action
                for action_name, action_config in action_configs.items():
                    if action_name not in self.actions:
                        log_func(f"Unknown action: {action_name}, skipping")
                        completed_operations += 1
                        if progress_callback:
                            progress_callback(completed_operations / total_operations)
                        continue

                    action = self.actions[action_name]
                    log_func(f"Executing {action_name} for account {account_id}")

                    success = await action.execute(
                        account_id, account_data, action_config, log_func, browser
                    )

                    log_func(
                        f"{action_name} {'succeeded' if success else 'failed'} for account {account_id}"
                    )

                    completed_operations += 1
                    if progress_callback:
                        progress_callback(completed_operations / total_operations)

                    # Add a random delay between actions
                    await asyncio.sleep(random.uniform(2.0, 5.0))

                # Close the browser context after all actions for this account
                if browser and not (hasattr(browser, '_closed') and browser._closed):
                    try:
                        await browser.close()
                        log_func(f"Closed browser for account {account_id}")
                    except Exception as e:
                        log_func(f"Error closing browser for account {account_id}: {str(e)}")

                # Add delay between accounts to reduce contention
                await asyncio.sleep(random.uniform(5.0, 10.0))

        except Exception as e:
            log_func(f"Error during workflow {workflow_name}: {str(e)}")
            return False
        finally:
            # Ensure all Playwright instances are closed
            if self.playwright:
                try:
                    await self.playwright.__aexit__(None, None, None)
                    log_func(f"Closed Playwright instance for workflow {workflow_name}")
                except Exception as e:
                    log_func(f"Error closing Playwright instance for workflow {workflow_name}: {str(e)}")
                self.playwright = None

        log_func(f"Completed workflow: {workflow_name}")
        return True