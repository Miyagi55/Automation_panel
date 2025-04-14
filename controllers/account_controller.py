"""
Account controller to handle account operations.
"""

import asyncio
import threading
from typing import Any, Callable, Dict, List, Optional

from models.account_model import AccountModel
from models.playwright.session_handler import SessionHandler
from utils.logger import logger

ACCOUNT_TEST_BROWSER_TIMEOUT_SECONDS = 300  # 5 minutes, edit as needed


class AccountController:
    """
    Controller for account operations.
    Handles the business logic between account model and view.
    """

    def __init__(self, update_ui_callback: Optional[Callable] = None):
        self.account_model = AccountModel()
        self.session_handler = SessionHandler()
        self.update_ui_callback = update_ui_callback

    def add_account(self, user: str, password: str) -> Optional[str]:
        """Add a new account."""
        if not user or not password:
            logger.warning("Username and password required")
            return None

        account_id = self.account_model.add_account(user, password)
        if account_id:
            logger.info(
                f"Added account: {user} (ID: {account_id}, Total: {len(self.account_model.accounts)})"
            )
            if self.update_ui_callback:
                self.update_ui_callback()
            return account_id
        else:
            logger.warning(f"Failed to add account: {user}")
            return None

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
        """Get a single account."""
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
                        user, password = line.strip().split(",")
                        account_id = self.add_account(user, password)
                        if account_id:
                            count += 1
                    except ValueError:
                        logger.warning(f"Invalid line in import file: {line.strip()}")
                logger.info(f"Imported {count} accounts from {file_path}")
                return count
        except Exception as e:
            logger.error(f"Error importing accounts: {str(e)}")
            return 0

    def test_account(self, account_id: str) -> None:
        """Test a single account login."""
        account = self.account_model.get_account(account_id)
        if not account:
            logger.warning(f"Account not found: {account_id}")
            return

        # Update account status to indicate testing
        self.update_account_status(account_id, "Testing")

        # Run the test in a separate thread
        def run_test():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                result = loop.run_until_complete(
                    self.session_handler.login_account(
                        account_id,
                        account["user"],
                        account["password"],
                        logger.info,
                        keep_browser_open_seconds=ACCOUNT_TEST_BROWSER_TIMEOUT_SECONDS,
                    )
                )

                # Update account status based on result
                if result:
                    self.update_account_status(
                        account_id, "Logged In", "Available", "Successful login"
                    )
                else:
                    self.update_account_status(
                        account_id, "Login Failed", "Inactive", "Failed login attempt"
                    )
            finally:
                loop.close()

        # Start the test thread
        thread = threading.Thread(target=run_test)
        thread.daemon = True
        thread.start()

    def test_multiple_accounts(self, account_ids: List[str]) -> None:
        """Test multiple accounts in batches."""
        # Prepare account data for testing
        accounts_to_test = []
        for account_id in account_ids:
            account = self.account_model.get_account(account_id)
            if account:
                # Update account status to indicate testing
                self.update_account_status(account_id, "Testing")

                accounts_to_test.append(
                    {
                        "account_id": account_id,
                        "user": account["user"],
                        "password": account["password"],
                    }
                )

        # Run tests in a separate thread
        def run_tests():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                results = loop.run_until_complete(
                    self.session_handler.test_multiple_accounts(
                        accounts_to_test, logger.info
                    )
                )

                # Update account statuses based on results
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

        # Start the tests thread
        thread = threading.Thread(target=run_tests)
        thread.daemon = True
        thread.start()
