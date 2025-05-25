"""
Cross-platform notification utilities for system alerts and messages.
"""

import platform
import threading
import time
from typing import Optional

from app.utils.logger import logger

try:
    from plyer import notification as plyer_notification

    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    logger.warning("plyer not available - notifications will be disabled")

# Platform-specific fallbacks
SYSTEM_PLATFORM = platform.system().lower()


class NotificationManager:
    """
    Cross-platform notification manager for resource alerts and other events.
    Handles rate limiting to prevent notification spam.
    """

    def __init__(self):
        """Initialize the notification manager."""
        self._last_notification_times = {}
        self._notification_cooldown = 300  # 5 minutes cooldown per notification type
        self._enabled = True
        self._app_name = "Automation Panel"

        if PLYER_AVAILABLE:
            logger.info(f"Notifications initialized for {SYSTEM_PLATFORM}")
        else:
            logger.warning("Notifications disabled - plyer not available")

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable notifications."""
        self._enabled = enabled
        logger.info(f"Notifications {'enabled' if enabled else 'disabled'}")

    def set_cooldown(self, cooldown_seconds: int) -> None:
        """Set the cooldown period between similar notifications."""
        self._notification_cooldown = max(60, cooldown_seconds)  # Minimum 1 minute
        logger.info(f"Notification cooldown set to {cooldown_seconds} seconds")

    def set_app_name(self, app_name: str) -> None:
        """Set the application name shown in notifications."""
        self._app_name = app_name
        logger.info(f"Notification app name set to: {app_name}")

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
        Show a cross-platform toast notification.

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
        if not self._enabled or not PLYER_AVAILABLE:
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
        """Show the actual toast notification using plyer."""
        try:
            # Prepare notification parameters
            notification_kwargs = {
                "title": title,
                "message": message,
                "app_name": self._app_name,
                "timeout": duration,
            }

            # Add icon if provided and file exists
            if icon_path:
                try:
                    import os

                    if os.path.exists(icon_path):
                        notification_kwargs["app_icon"] = icon_path
                except Exception as e:
                    logger.debug(f"Could not set icon: {e}")

            # Show notification using plyer
            plyer_notification.notify(**notification_kwargs)

        except Exception as e:
            logger.error(f"Error showing cross-platform notification: {str(e)}")
            # Fallback to system-specific methods if plyer fails
            self._fallback_notification(title, message)

    def _fallback_notification(self, title: str, message: str) -> None:
        """Fallback notification methods for when plyer fails."""
        try:
            if SYSTEM_PLATFORM == "windows":
                # Windows fallback using ctypes for system tray
                import ctypes

                ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
            elif SYSTEM_PLATFORM == "darwin":
                # macOS fallback using osascript
                import subprocess

                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(["osascript", "-e", script], check=False)
            elif SYSTEM_PLATFORM == "linux":
                # Linux fallback using notify-send
                import subprocess

                subprocess.run(["notify-send", title, message], check=False)
            else:
                logger.warning(
                    f"No fallback notification method for platform: {SYSTEM_PLATFORM}"
                )
        except Exception as e:
            logger.error(f"Fallback notification failed: {e}")

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

    def show_captcha_alert(self, account_id: str) -> bool:
        """Show a captcha detection alert notification."""
        return self.show_notification(
            title="Captcha Detected",
            message=f"Manual intervention required for account {account_id}",
            notification_type="captcha_alert",
            duration=15,
        )


# Global notification manager instance
notification_manager = NotificationManager()
