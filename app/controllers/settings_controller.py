"""
Settings controller to manage application settings.
"""

import os
from typing import Any, Dict, List, Tuple

from app.utils.logger import logger
from app.utils.session_sync import SessionInfo, SessionSyncService, SyncResult


class SettingsController:
    """
    Controller for application settings.
    Manages configuration options and settings persistence.
    """

    def __init__(self):
        """Initialize the settings controller."""
        self.settings = self._load_default_settings()

    def _load_default_settings(self) -> Dict[str, Any]:
        """Load default settings."""
        return {
            "monitoring_interval": 1.0,
            "browser_concurrency": 5,
            "default_directory": os.path.expanduser("~"),
            "headless_mode": False,
            "auto_save": True,
        }

    def get_setting(self, key: str) -> Any:
        """Get a setting value by key."""
        return self.settings.get(key)

    def update_setting(self, key: str, value: Any) -> bool:
        """Update a setting value."""
        if key in self.settings:
            self.settings[key] = value
            logger.info(f"Updated setting: {key}={value}")
            return True
        logger.warning(f"Unknown setting: {key}")
        return False

    def update_settings(self, new_settings: Dict[str, Any]) -> bool:
        """Update multiple settings at once."""
        for key, value in new_settings.items():
            if key not in self.settings:
                logger.warning(f"Unknown setting: {key}")
                continue
            self.settings[key] = value
        logger.info(f"Updated {len(new_settings)} settings")
        return True

    def save_settings(self) -> bool:
        """Save settings to a file or database."""
        try:
            # In a full implementation, this would save to a file or database
            # For now, just log that we're saving
            logger.info("Settings saved")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            return False

    def load_settings(self) -> bool:
        """Load settings from a file or database."""
        try:
            # In a full implementation, this would load from a file or database
            # For now, just use defaults
            self.settings = self._load_default_settings()
            logger.info("Settings loaded")
            return True
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")
            return False

    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        self.settings = self._load_default_settings()
        logger.info("Settings reset to defaults")

    def analyze_session_sync_status(self) -> Tuple[List[SessionInfo], List[str]]:
        """
        Analyze the current sync status between session folders and accounts.json.

        Returns:
            Tuple of (orphan_sessions, orphan_accounts)
        """
        session_sync = SessionSyncService()
        return session_sync.analyze_sync_status()

    def sync_sessions(self, prune: bool = False) -> SyncResult:
        """
        Synchronize session folders with accounts.json.

        Args:
            prune: Whether to remove orphan account entries

        Returns:
            SyncResult with details of the sync operation
        """
        session_sync = SessionSyncService()
        result = session_sync.sync_sessions(prune=prune)
        logger.info(
            f"Session sync completed: {result.added_count} added, {result.pruned_count} pruned"
        )
        return result
