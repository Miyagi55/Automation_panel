"""
Account model to manage Facebook accounts data.
"""

import json
import os
from typing import Any, Dict, Optional


class AccountModel:
    """
    Account model to manage Facebook accounts data.
    Handles loading, saving, and manipulating account data.
    """

    def __init__(self, accounts_file: str = "accounts.json"):
        self.accounts_file = accounts_file
        self.accounts: Dict[str, Dict[str, Any]] = self.load_accounts()
        self.next_id = self._get_next_id()

    def load_accounts(self) -> Dict[str, Dict[str, Any]]:
        """Load accounts from a JSON file."""
        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading accounts: {str(e)}")
        return {}

    def save_accounts(self) -> bool:
        """Save accounts to a JSON file."""
        try:
            with open(self.accounts_file, "w") as f:
                json.dump(self.accounts, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving accounts: {str(e)}")
            return False

    def _get_next_id(self) -> int:
        """Determine the next ID based on existing accounts."""
        if not self.accounts:
            return 1
        max_id = max(int(account_id) for account_id in self.accounts.keys())
        return max_id + 1

    def add_account(self, user: str, password: str) -> Optional[str]:
        """Add a new account."""
        if not user or not password:
            return None

        if any(acc.get("user") == user for acc in self.accounts.values()):
            return None

        try:
            account_id = f"{self.next_id:03d}"
            self.next_id += 1

            account_data = {
                "id": account_id,
                "user": user,
                "password": password,
                "activity": "Inactive",
                "status": "Logged Out",
                "last_activity": "",
                "proxy": "",
                "user_agent": "",
                "cookies": {},
            }
            self.accounts[account_id] = account_data
            self.save_accounts()
            return account_id
        except Exception as e:
            print(f"Error adding account: {str(e)}")
            return None

    def update_account(self, account_id: str, user: str, password: str) -> bool:
        """Update an existing account."""
        if account_id not in self.accounts:
            return False

        old_user = self.accounts[account_id]["user"]
        if user != old_user and any(
            acc.get("user") == user
            for acc_id, acc in self.accounts.items()
            if acc_id != account_id
        ):
            return False

        self.accounts[account_id].update({"user": user, "password": password})
        self.save_accounts()
        return True

    def delete_account(self, account_id: str) -> bool:
        """Delete an account."""
        if account_id not in self.accounts:
            return False
        del self.accounts[account_id]
        self.save_accounts()
        return True

    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get a single account."""
        return self.accounts.get(account_id)

    def get_all_accounts(self) -> Dict[str, Dict[str, Any]]:
        """Get all accounts."""
        return self.accounts

    def update_account_status(
        self,
        account_id: str,
        status: str,
        activity: Optional[str] = None,
        last_activity: Optional[str] = None,
    ) -> bool:
        """Update account status."""
        if account_id not in self.accounts:
            return False

        if status:
            self.accounts[account_id]["status"] = status
        if activity:
            self.accounts[account_id]["activity"] = activity
        if last_activity:
            self.accounts[account_id]["last_activity"] = last_activity

        self.save_accounts()
        return True
