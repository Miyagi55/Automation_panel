"""
Automation controller to handle workflow operations.
"""

import asyncio
import json
import os
import random
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from app.models.account_model import AccountModel
from app.models.playwright.automation_handler import AutomationHandler
from app.utils.config import DATA_DIR
from app.utils.logger import logger


# ------------------------------class-----------------------------------------------------------#
class WorkflowModel:
    """
    Model for storing and retrieving workflow data.
    """

    def __init__(self, workflows_file: str = None):
        if workflows_file is None:
            self.workflows_file = str(DATA_DIR / "workflows.json")
        else:
            self.workflows_file = workflows_file
        self.workflows = self.load_workflows()

    def load_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Load workflows from a JSON file."""
        if os.path.exists(self.workflows_file):
            try:
                with open(self.workflows_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading workflows: {str(e)}")
        return {}

    def save_workflows(self) -> bool:
        """Save workflows to a JSON file."""
        try:
            # Make sure the directory exists
            os.makedirs(os.path.dirname(self.workflows_file), exist_ok=True)
            with open(self.workflows_file, "w") as f:
                json.dump(self.workflows, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Error saving workflows: {str(e)}")
            return False

    def add_workflow(
        self, name: str, actions: Dict[str, dict], accounts: List[str]
    ) -> bool:
        """Add a new workflow."""
        if name in self.workflows:
            logger.warning(f"Workflow already exists: {name}")
            return False

        self.workflows[name] = {"actions": actions, "accounts": accounts}
        return self.save_workflows()

    def get_workflow(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a single workflow."""
        return self.workflows.get(name)

    def get_all_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get all workflows."""
        return self.workflows

    def delete_workflow(self, name: str) -> bool:
        """Delete a workflow."""
        if name not in self.workflows:
            return False
        del self.workflows[name]
        return self.save_workflows()


# ------------------------------class-----------------------------------------------------------#
class AutomationController:
    """
    Controller for automation operations.
    Handles the business logic between workflow model and view.
    """

    def __init__(
        self,
        update_ui_callback: Optional[Callable] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ):
        self.workflow_model = WorkflowModel()
        self.account_model = AccountModel()
        self.automation_handler = AutomationHandler()
        self.update_ui_callback = update_ui_callback
        self.progress_callback = progress_callback
        self.running = False
        self.stop_requested = False

    # --------------Manage Workflows---------------------------------------#
    def save_workflow(
        self, name: str, actions: Dict[str, dict], accounts: List[str]
    ) -> bool:
        """Save a new workflow."""
        if not name:
            logger.warning("Workflow name is required")
            return False

        if not actions:
            logger.warning("No actions specified for workflow")
            return False

        if not accounts:
            logger.warning("No accounts selected for workflow")
            return False

        success = self.workflow_model.add_workflow(name, actions, accounts)
        if success:
            logger.info(
                f"Saved workflow: {name} with {len(actions)} actions and {len(accounts)} accounts"
            )
            if self.update_ui_callback:
                self.update_ui_callback()
            return True
        else:
            logger.warning(f"Failed to save workflow: {name}")
            return False

    def delete_workflow(self, name: str) -> bool:
        """Delete a workflow."""
        success = self.workflow_model.delete_workflow(name)
        if success:
            logger.info(f"Deleted workflow: {name}")
            if self.update_ui_callback:
                self.update_ui_callback()
            return True
        else:
            logger.warning(f"Failed to delete workflow: {name}")
            return False

    def get_all_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get all workflows."""
        return self.workflow_model.get_all_workflows()

    def get_workflow(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a single workflow."""
        return self.workflow_model.get_workflow(name)

    # ---------Automation------------------------------------------------#
    def start_automation(
        self, selected_workflows: List[str], interval: int, randomize: bool
    ) -> bool:
        """Start automation for selected workflows."""
        if self.running:
            logger.warning("Automation is already running")
            return False

        if not selected_workflows:
            logger.warning("No workflows selected")
            return False

        # Verify all selected workflows exist
        for name in selected_workflows:
            if not self.workflow_model.get_workflow(name):
                logger.warning(f"Workflow not found: {name}")
                return False

        # Start the automation in a separate thread
        self.running = True
        self.stop_requested = False

        thread = threading.Thread(
            target=self._run_automation,
            args=(selected_workflows, interval, randomize, False),
        )
        thread.daemon = True
        thread.start()

        logger.info(
            f"Started automation for {len(selected_workflows)} workflows with interval {interval}s"
        )
        return True

    def stop_automation(self) -> bool:
        """Stop the currently running automation."""
        if not self.running:
            logger.warning("No automation is running")
            return False

        self.stop_requested = True
        logger.info("Stopping automation...")
        return True

    def _run_automation(
        self,
        selected_workflows: List[str],
        interval: int,
        randomize: bool,
        repeat: bool = False,
    ) -> None:
        """Run the automation loop for selected workflows."""
        try:
            if repeat:
                while not self.stop_requested:
                    for i, workflow_name in enumerate(selected_workflows):
                        if self.stop_requested:
                            break

                        workflow_data = self.workflow_model.get_workflow(workflow_name)
                        if not workflow_data:
                            continue

                        # Update workflow status
                        logger.info(f"Running workflow: {workflow_name}")
                        if self.progress_callback:
                            self.progress_callback(workflow_name, 0.0)

                        # Run the workflow
                        self._execute_workflow(workflow_name, workflow_data)

                        # Don't wait after the last workflow if stopping
                        if self.stop_requested:
                            break

                        # Skip delay if this is the last workflow
                        if i < len(selected_workflows) - 1:
                            # Wait before the next workflow
                            delay = interval
                            if randomize:
                                # Randomize by +/- 20%
                                delay = int(interval * (0.8 + 0.4 * random.random()))

                            logger.info(f"Waiting {delay}s before next workflow")

                            # Wait in small increments to allow for quick stopping
                            start_time = time.time()
                            while time.time() - start_time < delay:
                                if self.stop_requested:
                                    break
                                time.sleep(1)
            else:
                for i, workflow_name in enumerate(selected_workflows):
                    if self.stop_requested:
                        break

                    workflow_data = self.workflow_model.get_workflow(workflow_name)
                    if not workflow_data:
                        continue

                    # Update workflow status
                    logger.info(f"Running workflow: {workflow_name}")
                    if self.progress_callback:
                        self.progress_callback(workflow_name, 0.0)

                    # Run the workflow
                    self._execute_workflow(workflow_name, workflow_data)

                    # Don't wait after the last workflow if stopping
                    if self.stop_requested:
                        break

                    # Skip delay if this is the last workflow
                    if i < len(selected_workflows) - 1:
                        # Wait before the next workflow
                        delay = interval
                        if randomize:
                            # Randomize by +/- 20%
                            delay = int(interval * (0.8 + 0.4 * random.random()))

                        logger.info(f"Waiting {delay}s before next workflow")

                        # Wait in small increments to allow for quick stopping
                        start_time = time.time()
                        while time.time() - start_time < delay:
                            if self.stop_requested:
                                break
                            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Caught KeyboardInterrupt, cleaning up...")
            self.cleanup()
        finally:
            self.running = False
            logger.info("Automation stopped")

    def _execute_workflow(
        self, workflow_name: str, workflow_data: Dict[str, Any]
    ) -> None:
        """Execute a single workflow."""

        def update_progress(progress: float) -> None:
            """Update progress callback for the workflow."""
            if self.progress_callback:
                self.progress_callback(workflow_name, progress)

        def run_workflow():
            """Run the workflow in a new asyncio loop."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                accounts = self.account_model.get_all_accounts()
                loop.run_until_complete(
                    self.automation_handler.execute_workflow(
                        workflow_name,
                        workflow_data,
                        accounts,
                        logger.info,
                        update_progress,
                    )
                )
            finally:
                # Cancel pending tasks and close the loop
                tasks = [
                    task
                    for task in asyncio.all_tasks(loop)
                    if task is not asyncio.current_task(loop)
                ]
                for task in tasks:
                    task.cancel()
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()

        # Run the workflow in a separate thread
        workflow_thread = threading.Thread(target=run_workflow)
        workflow_thread.daemon = True
        workflow_thread.start()
        workflow_thread.join()  # Wait for workflow to complete

    def cleanup(self):
        """Clean up resources on program termination."""
        loop = asyncio.get_event_loop()
        tasks = [
            task
            for task in asyncio.all_tasks(loop)
            if task is not asyncio.current_task(loop)
        ]
        for task in tasks:
            task.cancel()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        logger.info("Cleaned up asyncio tasks and loop")

        # Close any open browser contexts and stop Playwright instances
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                self.automation_handler.session_handler.batch_processor.cleanup(
                    logger.info
                )
            )
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
        logger.info("Completed cleanup of browser contexts and Playwright instances")
