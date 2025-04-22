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
        
        return self.account_model.get_all_accounts()

    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        
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
                        # Strip whitespace from the line
                        line = line.strip()
                        # Check for either ':' or ',' as separator
                        if ':' in line:
                            user, password = line.split(':')
                        elif ',' in line:
                            user, password = line.split(',')
                        else:
                            logger.warning(f"Invalid line in import file: {line}")
                            continue
                        # Strip whitespace from user and password
                        user = user.strip()
                        password = password.strip()
                        # Add account and increment count if successful
                        account_id = self.add_account(user, password)
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

        # Extract account IDs for open_sessions
        account_id_list = [account["account_id"] for account in accounts_to_run]

        # Run in a separate thread
        def run_async_sessions():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                results = loop.run_until_complete(
                    self.session_handler.open_sessions(
                        account_id_list,
                        logger.info,
                        keep_browser_open_seconds=ACCOUNT_TEST_BROWSER_TIMEOUT_SECONDS
                    )
                )

                # Update account statuses based on results
                logger.info(f"Results from run_browser - Type: {type(results)}, Items: {results.items()}")
                for account_id, success in results.items():
                    if success:
                        self.update_account_status(
                            account_id, "Logged In", "Available", "Successful session open"
                        )
                    else:
                        self.update_account_status(
                            account_id,
                            "Session Failed",
                            "Inactive",
                            "Failed to open session",
                        )
            finally:
                loop.close()

        # Start the tests thread
        thread = threading.Thread(target=run_async_sessions)
        thread.daemon = True
        thread.start()

    def auto_login_accounts(self, account_ids: List[str]) -> None:
        """Test multiple accounts in batches."""
        # Prepare account data for testing
        accounts_to_login = []
        for account_id in account_ids:
            account = self.account_model.get_account(account_id)
            if account:
                # Update account status to indicate testing
                self.update_account_status(account_id, "Login")
                accounts_to_login.append(
                    {
                        "account_id": account_id,
                        "user": account["user"],
                        "password": account["password"],
                    }
                )

        # Run in a separate thread
        def run_auto_login_accs():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                results = loop.run_until_complete(
                    self.session_handler.auto_login_accounts(
                        accounts_to_login, logger.info
                    )
                )

                # Update account statuses based on results logger
                for account_id, success in results.items():
                    if success:
                        self.update_account_status(
                            account_id, "Logged In", "Available", "Successful login"
                        )
                    else:
                        self.update_account_status(
                            account_id,
                            "Login Failed",
                            "Inactive",
                            "Failed login attempt",
                        )
            finally:
                loop.close()

        # Start thread
        thread = threading.Thread(target=run_auto_login_accs)
        thread.daemon = True
        thread.start()