"""
Settings controller to manage application settings.
"""

import os
from typing import Any, Dict

from app.utils.logger import logger


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
            # Notification settings
            "notifications_enabled": True,
            "notification_cooldown": 300,  # 5 minutes between similar notifications
            # Resource alert thresholds
            "memory_alert_threshold": 85.0,  # Percentage
            "storage_alert_threshold": 90.0,  # Percentage
            "cpu_alert_threshold": 90.0,  # Percentage
            "memory_critical_threshold": 95.0,  # Critical memory threshold
            "storage_critical_threshold": 95.0,  # Critical storage threshold
            # Recovery notification thresholds (when to notify that system recovered)
            "memory_recovery_threshold": 75.0,  # When memory drops below this after alert
            "storage_recovery_threshold": 80.0,  # When storage drops below this after alert
            "cpu_recovery_threshold": 70.0,  # When CPU drops below this after alert
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

    def get_notification_settings(self) -> Dict[str, Any]:
        """Get all notification-related settings."""
        notification_keys = [
            "notifications_enabled",
            "notification_cooldown",
            "memory_alert_threshold",
            "storage_alert_threshold",
            "cpu_alert_threshold",
            "memory_critical_threshold",
            "storage_critical_threshold",
            "memory_recovery_threshold",
            "storage_recovery_threshold",
            "cpu_recovery_threshold",
        ]
        return {
            key: self.settings.get(key)
            for key in notification_keys
            if key in self.settings
        }

    def update_notification_settings(
        self, notification_settings: Dict[str, Any]
    ) -> bool:
        """Update notification-specific settings with validation."""
        valid_keys = [
            "notifications_enabled",
            "notification_cooldown",
            "memory_alert_threshold",
            "storage_alert_threshold",
            "cpu_alert_threshold",
            "memory_critical_threshold",
            "storage_critical_threshold",
            "memory_recovery_threshold",
            "storage_recovery_threshold",
            "cpu_recovery_threshold",
        ]

        updated_count = 0
        for key, value in notification_settings.items():
            if key not in valid_keys:
                logger.warning(f"Invalid notification setting: {key}")
                continue

            # Validate threshold values
            if key.endswith("_threshold") and isinstance(value, (int, float)):
                if not (0 <= value <= 100):
                    logger.warning(
                        f"Invalid threshold value for {key}: {value} (must be 0-100)"
                    )
                    continue
            elif key == "notification_cooldown" and isinstance(value, (int, float)):
                if value < 60:
                    logger.warning(
                        f"Invalid cooldown value: {value} (minimum 60 seconds)"
                    )
                    continue
            elif key == "notifications_enabled" and not isinstance(value, bool):
                logger.warning(f"Invalid boolean value for {key}: {value}")
                continue

            self.settings[key] = value
            updated_count += 1

        if updated_count > 0:
            logger.info(f"Updated {updated_count} notification settings")
            return True
        return False
