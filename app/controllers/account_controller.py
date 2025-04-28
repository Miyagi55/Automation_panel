import asyncio
import threading
from typing import Any, Callable, Dict, List, Optional

from app.models.account_model import AccountModel
from app.models.playwright.session_handler import SessionHandler
from app.utils.logger import logger
from app.utils.config import ACCOUNT_TEST_BROWSER_TIMEOUT_SECONDS


class AccountController:
    """
    Controller for account operations.
    Handles the business logic between account model and view.
    """

    def __init__(self, update_ui_callback: Optional[Callable] = None):
        self.account_model = AccountModel()
        self.session_handler = SessionHandler()
        self.update_ui_callback = update_ui_callback

    def add_account(self, user: str, password: str) -> tuple[Optional[str], Optional[str]]:
        """Add a new account."""
        if not user or not password:
            logger.warning("Username and password required")
            return None, "Username and password cannot be empty"

        account_id, error_message = self.account_model.add_account(user, password)
        if account_id:
            logger.info(
                f"Added account: {user} (ID: {account_id}, Total: {len(self.account_model.accounts)})"
            )
            if self.update_ui_callback:
                self.update_ui_callback()
            return account_id, None
        else:
            logger.warning(f"Failed to add account: {user}")
            return None, error_message or "Failed to add account"

    def update_account(self, account_id: str, user: str, password: str) -> bool:
        """Update an existing account."""
        if not account_id or not user or not password:
            logger.warning("Account ID, username, and password required")
            return False

        account = self.account_model.get_account(account_id)
        old_user = account["user"] if account else None

        success = self.account_model.update_account(account_id, user, password)

        if success:
            logger.info(f"Updated account: {old_user} -> {user} (ID: {account_id})")
            if self.update_ui_callback:
                self.update_ui_callback()
            return True
        else:
            logger.warning(f"Failed to update account: {old_user}")
            return False

    def delete_account(self, account_id: str) -> bool:
        """Delete an account."""
        account = self.account_model.get_account(account_id)
        if not account:
            logger.warning(f"Account not found: {account_id}")
            return False

        user = account["user"]
        success = self.account_model.delete_account(account_id)

        if success:
            logger.info(
                f"Deleted account: {user} (ID: {account_id}, Total: {len(self.account_model.accounts)})"
            )
            if self.update_ui_callback:
                self.update_ui_callback()
            return True
        else:
            logger.warning(f"Failed to delete account: {user}")
            return False

    def get_all_accounts(self) -> Dict[str, Dict[str, Any]]:
        """Get all accounts."""
        return self.account_model.get_all_accounts()

    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get a single account by ID."""
        return self.account_model.get_account(account_id)

    def update_account_status(
        self,
        account_id: str,
        status: str,
        activity: Optional[str] = None,
        last_activity: Optional[str] = None,
    ) -> bool:
        """Update account status."""
        success = self.account_model.update_account_status(
            account_id, status, activity, last_activity
        )
        if success:
            logger.info(f"Updated status for account {account_id}: {status}")
            if self.update_ui_callback:
                self.update_ui_callback()
            return True
        else:
            logger.warning(f"Failed to update status for account {account_id}")
            return False

    def import_accounts_from_file(self, file_path: str) -> int:
        """Import accounts from a file."""
        try:
            with open(file_path, "r") as f:
                count = 0
                for line in f:
                    try:
                        line = line.strip()
                        if ':' in line:
                            user, password = line.split(':')
                        elif ',' in line:
                            user, password = line.split(',')
                        else:
                            logger.warning(f"Invalid line in import file: {line}")
                            continue
                        user = user.strip()
                        password = password.strip()
                        account_id, _ = self.add_account(user, password)
                        if account_id:
                            count += 1
                    except ValueError:
                        logger.warning(f"Invalid line in import file: {line}")
                logger.info(f"Imported {count} accounts from {file_path}")
                return count
        except Exception as e:
            logger.error(f"Error importing accounts: {str(e)}")
            return 0

    def run_browser(self, account_ids: List[str]) -> None:
        """Test a single or multiple account logins by opening existing sessions."""
        accounts_to_run = []
        for account_id in account_ids:
            account = self.account_model.get_account(account_id)
            if account:
                self.update_account_status(account_id, "Running")
                accounts_to_run.append(
                    {
                        "account_id": account_id,
                        "user": account["user"],
                        "password": account["password"],
                    }
                )

        account_id_list = [account["account_id"] for account in accounts_to_run]

        async def run_sessions():
            try:
                results = await self.session_handler.open_sessions(
                    account_id_list,
                    logger.info,
                    keep_browser_open_seconds=ACCOUNT_TEST_BROWSER_TIMEOUT_SECONDS
                )

                for account_id, (login_success, sim_success) in results.items():
                    if login_success and sim_success:
                        self.update_account_status(
                            account_id,
                            "Logged In",
                            "Feed Simulated",
                            "Successful session and feed simulation"
                        )
                    elif login_success:
                        self.update_account_status(
                            account_id,
                            "Logged In",
                            "Simulation Failed" if sim_success is False else "No Simulation",
                            "Session opened but feed simulation failed" if sim_success is False else "Session opened, no simulation attempted"
                        )
                    else:
                        self.update_account_status(
                            account_id,
                            "Not Logged In",
                            "No Simulation",
                            "Session opened but not logged in"
                        )
            except Exception as e:
                logger.error(f"Error running browser sessions: {str(e)}")

        def run_async_sessions():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_sessions())
            finally:
                # Clean up any remaining tasks
                pending = asyncio.all_tasks(loop)
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()

        thread = threading.Thread(target=run_async_sessions)
        thread.daemon = True
        thread.start()

    def auto_login_accounts(self, account_ids: List[str]) -> None:
        """Test multiple accounts in batches."""
        accounts_to_login = []
        for account_id in account_ids:
            account = self.account_model.get_account(account_id)
            if account:
                self.update_account_status(account_id, "Login")
                accounts_to_login.append(
                    {
                        "account_id": account_id,
                        "user": account["user"],
                        "password": account["password"],
                    }
                )

        async def run_logins():
            try:
                results = await self.session_handler.auto_login_accounts(
                    accounts_to_login, logger.info
                )

                for account_id, (login_success, sim_success) in results.items():
                    if login_success and sim_success:
                        self.update_account_status(
                            account_id,
                            "Logged In",
                            "Feed Simulated",
                            "Successful login and feed simulation"
                        )
                    elif login_success:
                        self.update_account_status(
                            account_id,
                            "Logged In",
                            "Simulation Failed",
                            "Logged in but feed simulation failed"
                        )
                    else:
                        self.update_account_status(
                            account_id,
                            "Login Failed",
                            "Inactive",
                            "Failed to login or not logged in"
                        )
            except Exception as e:
                logger.error(f"Error running login sessions: {str(e)}")

        def run_async_logins():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_logins())
            finally:
                # Clean up any remaining tasks
                pending = asyncio.all_tasks(loop)
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()

        thread = threading.Thread(target=run_async_logins)
        thread.daemon = True
        thread.start()

    def simulate_feed_for_accounts(self, account_ids: List[str]) -> None:
        """Simulate Facebook feed interaction for multiple accounts."""
        accounts_to_simulate = []
        for account_id in account_ids:
            account = self.account_model.get_account(account_id)
            if account:
                self.update_account_status(account_id, "Simulating Feed")
                accounts_to_simulate.append(
                    {
                        "account_id": account_id,
                        "user": account["user"],
                        "password": account["password"],
                    }
                )

        account_id_list = [account["account_id"] for account in accounts_to_simulate]

        async def run_feed_simulation():
            for account_id in account_id_list:
                browser = await self.session_handler.browser_context.create_browser_context(account_id, logger.info)
                if not browser:
                    logger.info(f"Failed to create browser context for account {account_id}")
                    self.update_account_status(
                        account_id,
                        "Simulation Failed",
                        "Inactive",
                        "Failed to create browser context"
                    )
                    continue

                try:
                    success = await self.session_handler.simulate_facebook_feed(
                        account_id=account_id,
                        url="https://www.facebook.com",
                        browser=browser,
                        log_func=logger.info,
                        max_execution_time=60
                    )
                    if success:
                        self.update_account_status(
                            account_id,
                            "Feed Simulated",
                            "Active",
                            "Successful feed simulation"
                        )
                    else:
                        self.update_account_status(
                            account_id,
                            "Simulation Failed",
                            "Inactive",
                            "Failed feed simulation or not logged in"
                        )
                finally:
                    await browser.close()
                    if hasattr(browser, '_playwright_instance'):
                        await browser._playwright_instance.stop()
                    logger.info(f"Closed browser for feed simulation for account {account_id}")

        def run_async_simulation():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_feed_simulation())
            finally:
                # Clean up any remaining tasks
                pending = asyncio.all_tasks(loop)
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()

        thread = threading.Thread(target=run_async_simulation)
        thread.daemon = True
        thread.start()