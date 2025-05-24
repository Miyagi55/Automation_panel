"""
Monitoring view for displaying system resource usage and logs.
"""

import tkinter as tk
from typing import Any, Dict

import customtkinter as ctk

from app.utils.logger import logger

from .base_view import BaseView


class MonitoringView(BaseView):
    """
    View for displaying system resource usage and logs.
    """

    def __init__(self, parent, controllers: Dict[str, Any]):
        """Initialize the monitoring view."""
        super().__init__(parent, controllers)

        # Register this view as the UI logger
        logger.set_ui_callback(self.add_log)

    def setup_ui(self):
        """Set up the UI components."""
        self.create_header("Monitoring Dashboard")

        # Create log text area
        self.log_text = ctk.CTkTextbox(self, height=200)
        self.log_text.pack(
            pady=self.padding, padx=self.padding, fill="both", expand=True
        )

        # Create action buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(pady=(0, self.padding), padx=self.padding, fill="x")

        clear_button = ctk.CTkButton(
            button_frame, text="Clear Logs", command=self._clear_logs
        )
        clear_button.pack(side="left", padx=(0, self.padding))

        # Create resource monitors
        monitor_frame = ctk.CTkFrame(self)
        monitor_frame.pack(pady=(0, self.padding), padx=self.padding, fill="x")

        # CPU usage
        cpu_frame = ctk.CTkFrame(monitor_frame)
        cpu_frame.pack(
            side="left", fill="both", expand=True, padx=(0, self.padding // 2)
        )

        ctk.CTkLabel(cpu_frame, text="CPU Usage").pack(pady=(self.padding // 2, 0))
        self.cpu_progressbar = ctk.CTkProgressBar(cpu_frame, width=200)
        self.cpu_progressbar.pack(pady=self.padding // 2)
        self.cpu_label = ctk.CTkLabel(cpu_frame, text="0%")
        self.cpu_label.pack(pady=(0, self.padding // 2))

        # Memory usage
        mem_frame = ctk.CTkFrame(monitor_frame)
        mem_frame.pack(
            side="left", fill="both", expand=True, padx=(self.padding // 2, 0)
        )

        ctk.CTkLabel(mem_frame, text="Memory Usage").pack(pady=(self.padding // 2, 0))
        self.mem_progressbar = ctk.CTkProgressBar(mem_frame, width=200)
        self.mem_progressbar.pack(pady=self.padding // 2)
        self.mem_label = ctk.CTkLabel(mem_frame, text="0%")
        self.mem_label.pack(pady=(0, self.padding // 2))

        # Disk usage
        disk_frame = ctk.CTkFrame(self)
        disk_frame.pack(pady=(0, self.padding), padx=self.padding, fill="x")

        ctk.CTkLabel(disk_frame, text="Disk Usage").pack(pady=(self.padding // 2, 0))
        self.disk_progressbar = ctk.CTkProgressBar(disk_frame, width=400)
        self.disk_progressbar.pack(pady=self.padding // 2)
        self.disk_label = ctk.CTkLabel(disk_frame, text="0%")
        self.disk_label.pack(pady=(0, self.padding // 2))

        # Initialize progressbars
        self.cpu_progressbar.set(0)
        self.mem_progressbar.set(0)
        self.disk_progressbar.set(0)

        # Notification status section
        notification_status_frame = ctk.CTkFrame(self)
        notification_status_frame.pack(
            pady=(0, self.padding), padx=self.padding, fill="x"
        )

        ctk.CTkLabel(
            notification_status_frame,
            text="Notification Status",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", pady=(self.padding // 2, 0))

        # Create status indicators
        status_grid_frame = ctk.CTkFrame(notification_status_frame)
        status_grid_frame.pack(fill="x", pady=self.padding // 2)

        # Notifications enabled indicator
        self.notifications_status_label = ctk.CTkLabel(
            status_grid_frame, text="Notifications: Enabled", text_color="green"
        )
        self.notifications_status_label.pack(side="left", padx=(0, self.padding))

        # Alert status indicators
        self.memory_alert_label = ctk.CTkLabel(
            status_grid_frame, text="Memory: Normal", text_color="green"
        )
        self.memory_alert_label.pack(side="left", padx=(0, self.padding))

        self.storage_alert_label = ctk.CTkLabel(
            status_grid_frame, text="Storage: Normal", text_color="green"
        )
        self.storage_alert_label.pack(side="left", padx=(0, self.padding))

        self.cpu_alert_label = ctk.CTkLabel(
            status_grid_frame, text="CPU: Normal", text_color="green"
        )
        self.cpu_alert_label.pack(side="left")

    def refresh(self):
        """
        Update resource display if needed.
        This will be called periodically by the timer.
        """
        pass  # Resources are updated directly by controller callbacks

    def update_resources(self, resource_data: Dict[str, Any]):
        """
        Update the resource displays with current data.
        This is called by the monitoring controller when new data is available.
        """
        # Update CPU
        cpu_percent = resource_data["cpu"]["percent"] / 100.0  # Convert to 0-1 scale
        self.cpu_progressbar.set(cpu_percent)
        self.cpu_label.configure(text=f"CPU: {resource_data['cpu']['percent']}%")

        # Update memory
        mem_percent = resource_data["memory"]["percent"] / 100.0
        self.mem_progressbar.set(mem_percent)
        mem_used_gb = resource_data["memory"]["used"] / (1024**3)  # Convert to GB
        mem_total_gb = resource_data["memory"]["total"] / (1024**3)
        self.mem_label.configure(
            text=f"Memory: {resource_data['memory']['percent']}% ({mem_used_gb:.1f} GB / {mem_total_gb:.1f} GB)"
        )

        # Update disk
        disk_percent = resource_data["disk"]["percent"] / 100.0
        self.disk_progressbar.set(disk_percent)
        disk_used_gb = resource_data["disk"]["used"] / (1024**3)
        disk_total_gb = resource_data["disk"]["total"] / (1024**3)
        self.disk_label.configure(
            text=f"Disk: {resource_data['disk']['percent']}% ({disk_used_gb:.1f} GB / {disk_total_gb:.1f} GB)"
        )

        # Update notification status
        self._update_notification_status()

    def add_log(self, message: str):
        """Add a log message to the log text area."""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)  # Scroll to the end

    def _clear_logs(self):
        """Clear the log text area."""
        self.log_text.delete("1.0", tk.END)
        self.controllers["monitoring"].clear_logs()

    def _update_notification_status(self):
        """Update the notification status indicators."""
        try:
            # Check if notifications are enabled
            settings_controller = self.controllers["settings"]
            notification_settings = settings_controller.get_notification_settings()
            notifications_enabled = notification_settings.get(
                "notifications_enabled", True
            )

            if notifications_enabled:
                self.notifications_status_label.configure(
                    text="Notifications: Enabled", text_color="green"
                )
            else:
                self.notifications_status_label.configure(
                    text="Notifications: Disabled", text_color="orange"
                )

            # Get current alert states
            monitoring_controller = self.controllers["monitoring"]
            alert_states = monitoring_controller.get_alert_states()

            # Update memory alert status
            if alert_states.get("memory_alert", False):
                self.memory_alert_label.configure(
                    text="Memory: ALERT", text_color="red"
                )
            else:
                self.memory_alert_label.configure(
                    text="Memory: Normal", text_color="green"
                )

            # Update storage alert status
            if alert_states.get("storage_alert", False):
                self.storage_alert_label.configure(
                    text="Storage: ALERT", text_color="red"
                )
            else:
                self.storage_alert_label.configure(
                    text="Storage: Normal", text_color="green"
                )

            # Update CPU alert status
            if alert_states.get("cpu_alert", False):
                self.cpu_alert_label.configure(text="CPU: ALERT", text_color="red")
            else:
                self.cpu_alert_label.configure(text="CPU: Normal", text_color="green")

        except Exception as e:
            logger.error(f"Error updating notification status: {str(e)}")
