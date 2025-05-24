"""
Notification utilities for system alerts and messages.
"""

import threading
import time
from typing import Optional

from app.utils.logger import logger

try:
    from win10toast import ToastNotifier

    TOAST_AVAILABLE = True
except ImportError:
    TOAST_AVAILABLE = False
    logger.warning("win10toast not available - notifications will be disabled")


class NotificationManager:
    """
    Manages system notifications for resource alerts and other events.
    Handles rate limiting to prevent notification spam.
    """

    def __init__(self):
        """Initialize the notification manager."""
        self.toaster = ToastNotifier() if TOAST_AVAILABLE else None
        self._last_notification_times = {}
        self._notification_cooldown = 300  # 5 minutes cooldown per notification type
        self._enabled = True

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable notifications."""
        self._enabled = enabled
        logger.info(f"Notifications {'enabled' if enabled else 'disabled'}")

    def set_cooldown(self, cooldown_seconds: int) -> None:
        """Set the cooldown period between similar notifications."""
        self._notification_cooldown = max(60, cooldown_seconds)  # Minimum 1 minute
        logger.info(f"Notification cooldown set to {cooldown_seconds} seconds")

    def show_notification(
        self,
        title: str,
        message: str,
        notification_type: str = "general",
        duration: int = 10,
        icon_path: Optional[str] = None,
        threaded: bool = True,
    ) -> bool:
        """
        Show a toast notification.

        Args:
            title: Notification title
            message: Notification message
            notification_type: Type identifier for rate limiting
            duration: How long to show notification (seconds)
            icon_path: Optional path to notification icon
            threaded: Whether to show notification in a separate thread

        Returns:
            bool: True if notification was shown, False if rate limited or disabled
        """
        if not self._enabled or not TOAST_AVAILABLE:
            return False

        # Check rate limiting
        current_time = time.time()
        last_time = self._last_notification_times.get(notification_type, 0)

        if current_time - last_time < self._notification_cooldown:
            logger.debug(f"Notification rate limited: {notification_type}")
            return False

        # Update last notification time
        self._last_notification_times[notification_type] = current_time

        if threaded:
            # Show notification in a separate thread to avoid blocking
            thread = threading.Thread(
                target=self._show_toast,
                args=(title, message, duration, icon_path),
                daemon=True,
            )
            thread.start()
        else:
            self._show_toast(title, message, duration, icon_path)

        logger.info(f"Notification shown: {title} - {message}")
        return True

    def _show_toast(
        self, title: str, message: str, duration: int, icon_path: Optional[str]
    ) -> None:
        """Show the actual toast notification."""
        try:
            self.toaster.show_toast(
                title=title,
                msg=message,
                duration=duration,
                icon_path=icon_path,
                threaded=False,  # Already handled threading in public method
            )
        except Exception as e:
            logger.error(f"Error showing toast notification: {str(e)}")

    def show_memory_alert(self, memory_percent: float, available_gb: float) -> bool:
        """Show a memory usage alert notification."""
        return self.show_notification(
            title="Memory Usage Alert",
            message=f"Memory usage is at {memory_percent:.1f}%\nAvailable: {available_gb:.1f} GB",
            notification_type="memory_alert",
            duration=15,
        )

    def show_storage_alert(self, disk_percent: float, free_gb: float) -> bool:
        """Show a storage usage alert notification."""
        return self.show_notification(
            title="Storage Usage Alert",
            message=f"Disk usage is at {disk_percent:.1f}%\nFree space: {free_gb:.1f} GB",
            notification_type="storage_alert",
            duration=15,
        )

    def show_cpu_alert(self, cpu_percent: float) -> bool:
        """Show a CPU usage alert notification."""
        return self.show_notification(
            title="CPU Usage Alert",
            message=f"CPU usage is at {cpu_percent:.1f}%\nSystem may be overloaded",
            notification_type="cpu_alert",
            duration=15,
        )

    def show_system_recovery(self, metric_name: str) -> bool:
        """Show a system recovery notification."""
        return self.show_notification(
            title="System Recovery",
            message=f"{metric_name} usage has returned to normal levels",
            notification_type="system_recovery",
            duration=10,
        )


# Global notification manager instance
notification_manager = NotificationManager()
