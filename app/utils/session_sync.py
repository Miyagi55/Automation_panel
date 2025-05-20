import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.utils.config import ACCOUNTS_FILE, SESSIONS
from app.utils.logger import logger


class SessionInfo:
    """Information about a session folder."""

    id: str
    username: Optional[str]

    def __init__(self, id: str, username: Optional[str] = None):
        self.id = id
        self.username = username


class SyncResult:
    """Results of a sync operation."""

    orphan_sessions: List["SessionInfo"]
    orphan_accounts: List[str]
    synced_count: int
    added_count: int
    pruned_count: int

    def __init__(
        self,
        orphan_sessions: List["SessionInfo"],
        orphan_accounts: List[str],
        synced_count: int,
        added_count: int,
        pruned_count: int,
    ):
        self.orphan_sessions = orphan_sessions
        self.orphan_accounts = orphan_accounts
        self.synced_count = synced_count
        self.added_count = added_count
        self.pruned_count = pruned_count

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-like access for backwards compatibility."""
        return getattr(self, key)


class SessionSyncService:
    """
    Service to detect and reconcile mismatches between session folders and accounts.json.
    Provides functionality to sync orphaned sessions and prune missing entries.
    """

    def __init__(self, accounts_file: str = str(ACCOUNTS_FILE)):
        self.accounts_file = accounts_file
        self.sessions_dir = SESSIONS

    def get_session_folders(self) -> List[SessionInfo]:
        """
        Scans the sessions directory for session_* folders and extracts their IDs.
        Attempts to read cookie files to infer usernames if possible.

        Returns:
            List of SessionInfo objects containing session ID and optional username
        """
        session_folders = []

        if not os.path.exists(self.sessions_dir):
            logger.warning(f"Sessions directory does not exist: {self.sessions_dir}")
            return session_folders

        session_pattern = re.compile(r"session_(\d+)")

        for item in os.listdir(self.sessions_dir):
            folder_path = os.path.join(self.sessions_dir, item)
            if os.path.isdir(folder_path):
                match = session_pattern.match(item)
                if match:
                    session_id = match.group(1)
                    username = self._extract_username_from_session(folder_path)
                    session_folders.append(
                        SessionInfo(id=session_id, username=username)
                    )

        return session_folders

    def _extract_username_from_session(self, session_folder: str) -> Optional[str]:
        """
        Attempts to extract username from session cookies or other metadata files.
        This is a best-effort approach - it may not always succeed.

        Args:
            session_folder: Path to the session folder

        Returns:
            Username if found, None otherwise
        """
        # Look for cookies file that might contain c_user cookie
        storage_path = os.path.join(session_folder, "Default", "Network", "Cookies")
        if os.path.exists(storage_path):
            # Placeholder for actual cookie extraction logic if needed
            # For now, we'll return None as we're focusing on ID-based sync
            pass

        return None

    def get_account_ids(self) -> Set[str]:
        """
        Gets all account IDs from the accounts.json file.

        Returns:
            Set of account IDs
        """
        account_ids = set()

        if not os.path.exists(self.accounts_file):
            logger.warning(f"Accounts file does not exist: {self.accounts_file}")
            return account_ids

        try:
            with open(self.accounts_file, "r") as f:
                accounts = json.load(f)
                account_ids = set(accounts.keys())
        except Exception as e:
            logger.error(f"Error loading accounts: {str(e)}")

        return account_ids

    def analyze_sync_status(self) -> Tuple[List[SessionInfo], List[str]]:
        """
        Analyzes the current sync status between session folders and accounts.json.

        Returns:
            Tuple of (orphan_sessions, orphan_accounts)
        """
        session_infos = self.get_session_folders()
        session_ids = {info.id for info in session_infos}
        account_ids = self.get_account_ids()

        # Find orphan sessions (folders with no matching account entry)
        orphan_sessions = [info for info in session_infos if info.id not in account_ids]

        # Find orphan accounts (account entries with no matching session folder)
        orphan_accounts = list(account_ids - session_ids)

        return orphan_sessions, orphan_accounts

    def sync_sessions(self, prune: bool = False) -> SyncResult:
        """
        Synchronizes session folders with accounts.json.
        Creates new account entries for orphan sessions and
        optionally removes entries for orphan accounts.

        Args:
            prune: Whether to remove orphan account entries

        Returns:
            SyncResult with details of the sync operation
        """
        # Analyze current sync status
        orphan_sessions, orphan_accounts = self.analyze_sync_status()

        added_count = 0
        pruned_count = 0

        # Read existing accounts
        accounts: Dict[str, Dict[str, Any]] = {}
        try:
            with open(self.accounts_file, "r") as f:
                accounts = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            accounts = {}

        # Add entries for orphan sessions
        existing_ids = {int(id) for id in accounts.keys() if id.isdigit()}
        next_id = max(existing_ids) + 1 if existing_ids else 1

        for session_info in orphan_sessions:
            session_id = session_info.id

            # If ID already exists in accounts but wasn't found during analysis,
            # it means the folder name doesn't match the expected pattern
            if session_id in accounts:
                continue

            # Create new account entry
            username = session_info.username or "unknown"
            accounts[session_id] = {
                "id": session_id,
                "user": username,
                "password": "",
                "activity": "Inactive",
                "status": "Imported",
                "last_activity": "",
                "proxy": "",
                "user_agent": "",
                "cookies": {},
            }
            added_count += 1

        # Prune orphan accounts if requested
        if prune:
            for account_id in orphan_accounts:
                if account_id in accounts:
                    del accounts[account_id]
                    pruned_count += 1

        # Save updated accounts
        try:
            with open(self.accounts_file, "w") as f:
                json.dump(accounts, f, indent=4)
            logger.info(f"Sessions synced: {added_count} added, {pruned_count} pruned")
        except Exception as e:
            logger.error(f"Error saving accounts during sync: {str(e)}")

        return SyncResult(
            orphan_sessions=orphan_sessions,
            orphan_accounts=orphan_accounts,
            synced_count=len(accounts) - added_count + pruned_count,
            added_count=added_count,
            pruned_count=pruned_count,
        )
