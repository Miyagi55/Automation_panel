"""
Monitoring controller to handle system monitoring and logging.
"""

import datetime
import threading
import time
from typing import Any, Callable, Dict, Optional

import psutil

from app.utils.logger import logger
from app.utils.notifications import notification_manager


class MonitoringController:
    """
    Controller for system monitoring.
    Handles resource tracking, activity logging, and threshold-based notifications.
    """

    def __init__(
        self,
        update_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        settings_controller: Optional[Any] = None,
    ):
        self.update_callback = update_callback
        self.settings_controller = settings_controller
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.update_interval = 1.0  # seconds

        # Track alert states to prevent spam and enable recovery notifications
        self._alert_states = {
            "memory_alert": False,
            "storage_alert": False,
            "cpu_alert": False,
        }

    def start_monitoring(self) -> bool:
        """Start system resource monitoring."""
        if self.monitoring_active:
            logger.warning("Monitoring is already active")
            return False

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

        logger.info("Resource monitoring started")
        return True

    def stop_monitoring(self) -> bool:
        """Stop system resource monitoring."""
        if not self.monitoring_active:
            logger.warning("Monitoring is not active")
            return False

        self.monitoring_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)

        logger.info("Resource monitoring stopped")
        return True

    def set_update_interval(self, interval: float) -> None:
        """Set the update interval for resource monitoring."""
        if interval < 0.1:
            interval = 0.1  # Minimum 100ms
        elif interval > 10:
            interval = 10  # Maximum 10s

        self.update_interval = interval
        logger.info(f"Monitoring update interval set to {interval}s")

    def _monitor_resources(self) -> None:
        """Monitor system resources in a loop."""
        while self.monitoring_active:
            try:
                # Get current resource usage
                resource_data = self._get_resource_data()

                # Check thresholds and trigger notifications if needed
                self._check_resource_thresholds(resource_data)

                # Call the update callback with the data
                if self.update_callback:
                    try:
                        self.update_callback(resource_data)
                    except AttributeError:
                        # This can happen during initialization when UI components aren't ready
                        # Don't log every occurrence to avoid spam during startup
                        time.sleep(0.5)  # Short sleep and continue
                    except Exception as e:
                        # Log other exceptions
                        logger.error(f"Error in monitoring update callback: {str(e)}")

                # Sleep for the update interval
                time.sleep(self.update_interval)

            except Exception as e:
                logger.error(f"Error monitoring resources: {str(e)}")
                time.sleep(1)  # Sleep on error to prevent tight loop

    def _get_resource_data(self) -> Dict[str, Any]:
        """Get current system resource usage data."""
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "cpu": {
                "percent": cpu_percent,
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free,
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
            },
        }

    def log_activity(self, message: str, level: str = "INFO") -> None:
        """Log an activity message with timestamp."""
        if level == "INFO":
            logger.info(message)
        elif level == "WARNING":
            logger.warning(message)
        elif level == "ERROR":
            logger.error(message)
        elif level == "DEBUG":
            logger.debug(message)

    def clear_logs(self) -> None:
        """Clear logs from the UI if a clear callback is registered."""
        if hasattr(logger, "ui_callback") and hasattr(logger.ui_callback, "clear"):
            logger.ui_callback.clear()
            logger.info("Logs cleared")
        else:
            logger.info("No UI log clear callback registered")

    def _check_resource_thresholds(self, resource_data: Dict[str, Any]) -> None:
        """Check resource usage against thresholds and trigger notifications."""
        if not self.settings_controller:
            return

        # Get current notification settings
        notification_settings = self.settings_controller.get_notification_settings()

        if not notification_settings.get("notifications_enabled", True):
            return

        # Configure notification manager
        notification_manager.set_enabled(
            notification_settings.get("notifications_enabled", True)
        )
        notification_manager.set_cooldown(
            notification_settings.get("notification_cooldown", 300)
        )

        # Check memory usage
        self._check_memory_threshold(resource_data, notification_settings)

        # Check storage usage
        self._check_storage_threshold(resource_data, notification_settings)

        # Check CPU usage
        self._check_cpu_threshold(resource_data, notification_settings)

    def _check_memory_threshold(
        self, resource_data: Dict[str, Any], settings: Dict[str, Any]
    ) -> None:
        """Check memory usage threshold and trigger notifications."""
        memory_percent = resource_data["memory"]["percent"]
        available_gb = resource_data["memory"]["available"] / (1024**3)

        alert_threshold = settings.get("memory_alert_threshold", 85.0)
        recovery_threshold = settings.get("memory_recovery_threshold", 75.0)

        if memory_percent >= alert_threshold and not self._alert_states["memory_alert"]:
            # Trigger alert
            notification_manager.show_memory_alert(memory_percent, available_gb)
            self._alert_states["memory_alert"] = True
            logger.warning(f"Memory usage alert triggered: {memory_percent:.1f}%")

        elif memory_percent < recovery_threshold and self._alert_states["memory_alert"]:
            # System recovered
            notification_manager.show_system_recovery("Memory")
            self._alert_states["memory_alert"] = False
            logger.info(f"Memory usage recovered: {memory_percent:.1f}%")

    def _check_storage_threshold(
        self, resource_data: Dict[str, Any], settings: Dict[str, Any]
    ) -> None:
        """Check storage usage threshold and trigger notifications."""
        disk_percent = resource_data["disk"]["percent"]
        free_gb = resource_data["disk"]["free"] / (1024**3)

        alert_threshold = settings.get("storage_alert_threshold", 90.0)
        recovery_threshold = settings.get("storage_recovery_threshold", 80.0)

        if disk_percent >= alert_threshold and not self._alert_states["storage_alert"]:
            # Trigger alert
            notification_manager.show_storage_alert(disk_percent, free_gb)
            self._alert_states["storage_alert"] = True
            logger.warning(f"Storage usage alert triggered: {disk_percent:.1f}%")

        elif disk_percent < recovery_threshold and self._alert_states["storage_alert"]:
            # System recovered
            notification_manager.show_system_recovery("Storage")
            self._alert_states["storage_alert"] = False
            logger.info(f"Storage usage recovered: {disk_percent:.1f}%")

    def _check_cpu_threshold(
        self, resource_data: Dict[str, Any], settings: Dict[str, Any]
    ) -> None:
        """Check CPU usage threshold and trigger notifications."""
        cpu_percent = resource_data["cpu"]["percent"]

        alert_threshold = settings.get("cpu_alert_threshold", 90.0)
        recovery_threshold = settings.get("cpu_recovery_threshold", 70.0)

        if cpu_percent >= alert_threshold and not self._alert_states["cpu_alert"]:
            # Trigger alert
            notification_manager.show_cpu_alert(cpu_percent)
            self._alert_states["cpu_alert"] = True
            logger.warning(f"CPU usage alert triggered: {cpu_percent:.1f}%")

        elif cpu_percent < recovery_threshold and self._alert_states["cpu_alert"]:
            # System recovered
            notification_manager.show_system_recovery("CPU")
            self._alert_states["cpu_alert"] = False
            logger.info(f"CPU usage recovered: {cpu_percent:.1f}%")

    def get_alert_states(self) -> Dict[str, bool]:
        """Get current alert states."""
        return self._alert_states.copy()

    def reset_alert_states(self) -> None:
        """Reset all alert states (useful for testing or manual reset)."""
        self._alert_states = {
            "memory_alert": False,
            "storage_alert": False,
            "cpu_alert": False,
        }
        logger.info("Alert states reset")

    def test_notification(self, notification_type: str = "test") -> bool:
        """Test notification system by sending a test notification."""
        return notification_manager.show_notification(
            title="Test Notification",
            message="This is a test notification from the Automation Panel",
            notification_type=notification_type,
            duration=5,
        )
