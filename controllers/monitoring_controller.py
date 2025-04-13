"""
Monitoring controller to handle system monitoring and logging.
"""

import datetime
import threading
import time
from typing import Any, Callable, Dict, Optional

import psutil

from utils.logger import logger


class MonitoringController:
    """
    Controller for system monitoring.
    Handles resource tracking and activity logging.
    """

    def __init__(
        self, update_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.update_callback = update_callback
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.update_interval = 1.0  # seconds

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
