
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from app.utils.config import ACCOUNTS_FILE


class AccountModel:
    """
    Account model to manage Facebook accounts data.
    Handles loading, saving, and manipulating account data.
    """

    def __init__(
        self,
        accounts_file: str = str(ACCOUNTS_FILE),
    ):
        self.accounts_file = accounts_file
        self.accounts: Dict[str, Dict[str, Any]] = self.load_accounts()
        self.next_id = self._get_next_id()

    def load_accounts(self) -> Dict[str, Dict[str, Any]]:
        
        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading accounts: {str(e)}")
        return {}

    def save_accounts(self) -> bool:
        
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

    def add_account(self, user: str, password: str) -> tuple[Optional[str], Optional[str]]:
        
        if not user or not password:
            return None, "Username and Password cannot be empty"

        if any(acc.get("user") == user for acc in self.accounts.values()):
            return None, f"Username {user} already exists"

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
            return account_id, None
        except Exception as e:
            print(f"Error adding account: {str(e)}")
            return None, f"Failed to add account: {str(e)}"

    def update_account(self, account_id: str, user: str, password: str) -> bool:
        
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
        
        if account_id not in self.accounts:
            return False
        del self.accounts[account_id]
        self.save_accounts()
        return True

    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        
        return self.accounts.get(account_id)

    def get_all_accounts(self) -> Dict[str, Dict[str, Any]]:
        
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

    def update_account_cookies(self, account_id: str, cookies: list[dict]) -> bool:
        """Update cookies for a given account, merging with existing cookies, and save atomically."""
        if account_id not in self.accounts:
            return False
        # Store cookies as a list of dicts for compatibility with Playwright
        self.accounts[account_id]["cookies"] = cookies
        return self.save_accounts()
