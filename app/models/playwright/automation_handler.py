import asyncio
import random
from typing import Any, Callable, Dict, Optional

from .base_action import AutomationAction
from .browser_manager import BrowserManager
from .session_handler import SessionHandler
from .actions import LikeAction, CommentAction


class AutomationHandler:
    """
    Manages and executes automation actions.
    """

    def __init__(self):
        self.actions = {
            "Likes": LikeAction(),
            "Comments": CommentAction(),
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

        action_configs = workflow_data.get("actions", {})
        account_user = workflow_data.get("accounts", [])

        if not action_configs:
            log_func(f"No actions defined for workflow: {workflow_name}")
            return False

        if not account_user:
            log_func(f"No accounts selected for workflow: {workflow_name}")
            return False

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
            for account_id in account_ids:
                account_data = accounts[account_id]

                result = await self.session_handler.open_sessions(
                    account_id, log_func, keep_browser_open_seconds=0, skip_simulation=True
                )
                log_func(f"Session result for account {account_id}: {result}")
                is_logged_in, sim_success = result.get(account_id, (False, False))

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

                    await asyncio.sleep(random.uniform(2.0, 5.0))

                if browser and not (hasattr(browser, '_closed') and browser._closed):
                    try:
                        await browser.close()
                        log_func(f"Closed browser for account {account_id}")
                    except Exception as e:
                        log_func(f"Error closing browser for account {account_id}: {str(e)}")

                await asyncio.sleep(random.uniform(5.0, 10.0))

        except Exception as e:
            log_func(f"Error during workflow {workflow_name}: {str(e)}")
            return False
        finally:
            if self.playwright:
                try:
                    await self.playwright.__aexit__(None, None, None)
                    log_func(f"Closed Playwright instance for workflow {workflow_name}")
                except Exception as e:
                    log_func(f"Error closing Playwright instance for workflow {workflow_name}: {str(e)}")
                self.playwright = None

        log_func(f"Completed workflow: {workflow_name}")
        return True