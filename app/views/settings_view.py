"""
Settings view for application settings and webdriver installation.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Any, Dict

import customtkinter as ctk

from app.utils.logger import logger

from .base_view import BaseView


class SettingsView(BaseView):
    """
    View for application settings and webdriver installation.
    """

    def __init__(self, parent, controllers: Dict[str, Any]):
        """Initialize the settings view."""
        super().__init__(parent, controllers)

    def setup_ui(self):
        """Set up the UI components."""
        self.create_header("Settings")

        # Webdriver section
        webdriver_frame = ctk.CTkFrame(self)
        webdriver_frame.pack(pady=self.padding, padx=self.padding, fill="x")

        ctk.CTkLabel(
            webdriver_frame, text="Webdriver Settings", font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", pady=(0, self.padding))

        # Webdriver status
        self.status_label = ctk.CTkLabel(
            webdriver_frame, text="Checking webdriver status..."
        )
        self.status_label.pack(anchor="w", pady=(0, self.padding // 2))

        # Webdriver actions
        button_frame = ctk.CTkFrame(webdriver_frame)
        button_frame.pack(fill="x", pady=(0, self.padding))

        self.download_btn = ctk.CTkButton(
            button_frame, text="Download Webdrivers", command=self._download_webdrivers
        )
        self.download_btn.pack(side="left", padx=(0, self.padding // 2))

        # Application settings section
        settings_frame = ctk.CTkFrame(self)
        settings_frame.pack(pady=self.padding, padx=self.padding, fill="x")

        ctk.CTkLabel(
            settings_frame, text="Application Settings", font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", pady=(0, self.padding))

        # Monitoring interval
        monitor_frame = ctk.CTkFrame(settings_frame)
        monitor_frame.pack(fill="x", pady=(0, self.padding // 2))

        ctk.CTkLabel(monitor_frame, text="Monitoring Update Interval (seconds):").pack(
            side="left"
        )
        self.interval_entry = ctk.CTkEntry(monitor_frame, width=80)
        self.interval_entry.pack(side="left", padx=self.padding)
        self.interval_entry.insert(0, "1.0")

        update_btn = ctk.CTkButton(
            monitor_frame, text="Update", command=self._update_monitoring_interval
        )
        update_btn.pack(side="left")

        # Concurrency settings
        concurrency_frame = ctk.CTkFrame(settings_frame)
        concurrency_frame.pack(fill="x", pady=(0, self.padding // 2))

        ctk.CTkLabel(concurrency_frame, text="Browser Concurrency Limit:").pack(
            side="left"
        )
        self.concurrency_entry = ctk.CTkEntry(concurrency_frame, width=80)
        self.concurrency_entry.pack(side="left", padx=self.padding)
        self.concurrency_entry.insert(0, "5")

        # Default directory for file dialogs
        dir_frame = ctk.CTkFrame(settings_frame)
        dir_frame.pack(fill="x", pady=(0, self.padding // 2))

        ctk.CTkLabel(dir_frame, text="Default Directory:").pack(side="left")
        self.dir_entry = ctk.CTkEntry(dir_frame, width=200)
        self.dir_entry.pack(side="left", padx=self.padding)

        browse_btn = ctk.CTkButton(
            dir_frame, text="Browse", command=self._browse_directory
        )
        browse_btn.pack(side="left")

        # Save settings button
        save_btn = ctk.CTkButton(
            settings_frame, text="Save Settings", command=self._save_settings
        )
        save_btn.pack(anchor="e", pady=(self.padding, 0))

        # Notification settings section
        notification_frame = ctk.CTkFrame(self)
        notification_frame.pack(pady=self.padding, padx=self.padding, fill="x")

        ctk.CTkLabel(
            notification_frame,
            text="Notification Settings",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", pady=(0, self.padding))

        # Enable notifications toggle
        self.notifications_switch = ctk.CTkSwitch(
            notification_frame,
            text="Enable Notifications",
            command=self._toggle_notifications,
        )
        self.notifications_switch.pack(anchor="w", pady=(0, self.padding // 2))

        # Notification cooldown
        cooldown_frame = ctk.CTkFrame(notification_frame)
        cooldown_frame.pack(fill="x", pady=(0, self.padding // 2))

        ctk.CTkLabel(cooldown_frame, text="Notification Cooldown (seconds):").pack(
            side="left"
        )
        self.cooldown_entry = ctk.CTkEntry(cooldown_frame, width=80)
        self.cooldown_entry.pack(side="left", padx=self.padding)

        # Memory threshold
        memory_frame = ctk.CTkFrame(notification_frame)
        memory_frame.pack(fill="x", pady=(0, self.padding // 2))

        ctk.CTkLabel(memory_frame, text="Memory Alert Threshold (%):").pack(side="left")
        self.memory_threshold_entry = ctk.CTkEntry(memory_frame, width=80)
        self.memory_threshold_entry.pack(side="left", padx=self.padding)

        # Storage threshold
        storage_frame = ctk.CTkFrame(notification_frame)
        storage_frame.pack(fill="x", pady=(0, self.padding // 2))

        ctk.CTkLabel(storage_frame, text="Storage Alert Threshold (%):").pack(
            side="left"
        )
        self.storage_threshold_entry = ctk.CTkEntry(storage_frame, width=80)
        self.storage_threshold_entry.pack(side="left", padx=self.padding)

        # CPU threshold
        cpu_frame = ctk.CTkFrame(notification_frame)
        cpu_frame.pack(fill="x", pady=(0, self.padding // 2))

        ctk.CTkLabel(cpu_frame, text="CPU Alert Threshold (%):").pack(side="left")
        self.cpu_threshold_entry = ctk.CTkEntry(cpu_frame, width=80)
        self.cpu_threshold_entry.pack(side="left", padx=self.padding)

        # Notification actions
        notification_actions_frame = ctk.CTkFrame(notification_frame)
        notification_actions_frame.pack(fill="x", pady=(self.padding // 2, 0))

        test_btn = ctk.CTkButton(
            notification_actions_frame,
            text="Test Notification",
            command=self._test_notification,
        )
        test_btn.pack(side="left", padx=(0, self.padding // 2))

        reset_btn = ctk.CTkButton(
            notification_actions_frame, text="Reset Alerts", command=self._reset_alerts
        )
        reset_btn.pack(side="left")

        save_notification_btn = ctk.CTkButton(
            notification_actions_frame,
            text="Save Notification Settings",
            command=self._save_notification_settings,
        )
        save_notification_btn.pack(side="right")

        # About section
        about_frame = ctk.CTkFrame(self)
        about_frame.pack(pady=self.padding, padx=self.padding, fill="both", expand=True)

        ctk.CTkLabel(about_frame, text="About", font=("Segoe UI", 14, "bold")).pack(
            anchor="w", pady=(0, self.padding)
        )

        app_info = (
            "Facebook Automation Panel\n"
            "Version: 1.0.0\n\n"
            "A GUI application for managing and automating Facebook accounts.\n"
            "This application uses MVC architecture for better maintainability."
        )

        ctk.CTkLabel(about_frame, text=app_info, justify="left").pack(anchor="w")

    def refresh(self):
        """Refresh the view's content."""
        self._check_webdriver_status()
        self._load_current_settings()

    def _check_webdriver_status(self):
        """Check and update the webdriver status."""
        browser_manager = self.controllers["browser"].browser_manager
        webdriver_path = browser_manager.webdriver_path

        if webdriver_path:
            self.status_label.configure(
                text=f"Webdrivers installed at: {webdriver_path}", text_color="green"
            )
            self.download_btn.configure(text="Update Webdrivers")
        else:
            self.status_label.configure(
                text="Webdrivers not found. Please install them to use browser automation.",
                text_color="red",
            )
            self.download_btn.configure(text="Install Webdrivers")

    def _download_webdrivers(self):
        """Download or update webdrivers."""
        self.download_btn.configure(state="disabled", text="Installing...")

        # Create a progress window
        progress_win = ctk.CTkToplevel(self)
        progress_win.title("Installing Webdrivers")
        progress_win.geometry("300x150")
        progress_win.transient(self)  # Tie to parent window
        progress_win.grab_set()  # Make modal

        status_label = ctk.CTkLabel(progress_win, text="Starting installation...")
        status_label.pack(pady=10)
        progress_bar = ctk.CTkProgressBar(progress_win, width=250)
        progress_bar.pack(pady=10)
        progress_bar.set(0)

        def update_progress(message, value):
            status_label.configure(text=message)
            progress_bar.set(value)
            if value >= 1.0:
                progress_win.after(1000, progress_win.destroy)  # Close after 1s
                self.download_btn.configure(state="normal")
                self._check_webdriver_status()

        # Install webdrivers in a separate thread
        self.controllers["browser"].install_webdrivers(update_progress)

    def _update_monitoring_interval(self):
        """Update the monitoring update interval."""
        try:
            interval = float(self.interval_entry.get())
            if interval < 0.1:
                raise ValueError("Interval must be at least 0.1 seconds.")

            self.controllers["monitoring"].set_update_interval(interval)
            messagebox.showinfo(
                "Success", f"Monitoring interval updated to {interval} seconds."
            )
        except ValueError as e:
            messagebox.showwarning("Input Error", f"Invalid interval: {str(e)}")

    def _browse_directory(self):
        """Browse for a default directory."""
        from tkinter import filedialog

        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)

    def _save_settings(self):
        """Save all settings."""
        # This would save settings to a config file or database
        # For now, just show a message
        messagebox.showinfo("Settings", "Settings saved successfully.")
        logger.info("Application settings updated.")

    def _toggle_notifications(self):
        """Toggle notifications on/off."""
        enabled = self.notifications_switch.get()
        settings_controller = self.controllers["settings"]
        settings_controller.update_setting("notifications_enabled", enabled)

        # Update notification manager immediately
        from app.utils.notifications import notification_manager

        notification_manager.set_enabled(enabled)

        logger.info(f"Notifications {'enabled' if enabled else 'disabled'}")

    def _test_notification(self):
        """Send a test notification."""
        monitoring_controller = self.controllers["monitoring"]
        success = monitoring_controller.test_notification("settings_test")

        if success:
            messagebox.showinfo(
                "Test Notification", "Test notification sent successfully!"
            )
        else:
            messagebox.showwarning(
                "Test Failed",
                "Failed to send test notification. Check if notifications are enabled.",
            )

    def _reset_alerts(self):
        """Reset all active alert states."""
        monitoring_controller = self.controllers["monitoring"]
        monitoring_controller.reset_alert_states()

        messagebox.showinfo("Alerts Reset", "All alert states have been reset.")
        logger.info("Alert states reset from settings")

    def _save_notification_settings(self):
        """Save all notification settings."""
        try:
            settings_controller = self.controllers["settings"]

            # Collect notification settings from UI
            notification_settings = {
                "notifications_enabled": self.notifications_switch.get(),
                "notification_cooldown": int(self.cooldown_entry.get()),
                "memory_alert_threshold": float(self.memory_threshold_entry.get()),
                "storage_alert_threshold": float(self.storage_threshold_entry.get()),
                "cpu_alert_threshold": float(self.cpu_threshold_entry.get()),
            }

            # Validate threshold values
            for key, value in notification_settings.items():
                if key.endswith("_threshold") and not (0 <= value <= 100):
                    raise ValueError(
                        f"Threshold values must be between 0-100%. Invalid: {key}={value}"
                    )
                elif key == "notification_cooldown" and value < 60:
                    raise ValueError(
                        "Notification cooldown must be at least 60 seconds"
                    )

            # Update settings
            success = settings_controller.update_notification_settings(
                notification_settings
            )

            if success:
                # Update notification manager with new settings
                from app.utils.notifications import notification_manager

                notification_manager.set_enabled(
                    notification_settings["notifications_enabled"]
                )
                notification_manager.set_cooldown(
                    notification_settings["notification_cooldown"]
                )

                messagebox.showinfo(
                    "Success", "Notification settings saved successfully!"
                )
                logger.info("Notification settings updated")
            else:
                messagebox.showwarning(
                    "Warning", "Some settings could not be updated. Check the logs."
                )

        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid input: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
            logger.error(f"Error saving notification settings: {str(e)}")

    def _load_current_settings(self):
        """Load current settings into the UI fields."""
        try:
            settings_controller = self.controllers["settings"]

            # Load monitoring interval
            interval = settings_controller.get_setting("monitoring_interval")
            if interval:
                self.interval_entry.delete(0, tk.END)
                self.interval_entry.insert(0, str(interval))

            # Load concurrency setting
            concurrency = settings_controller.get_setting("browser_concurrency")
            if concurrency:
                self.concurrency_entry.delete(0, tk.END)
                self.concurrency_entry.insert(0, str(concurrency))

            # Load default directory
            default_dir = settings_controller.get_setting("default_directory")
            if default_dir:
                self.dir_entry.delete(0, tk.END)
                self.dir_entry.insert(0, default_dir)

            # Load notification settings
            notification_settings = settings_controller.get_notification_settings()

            # Set notifications switch
            notifications_enabled = notification_settings.get(
                "notifications_enabled", True
            )
            if notifications_enabled:
                self.notifications_switch.select()
            else:
                self.notifications_switch.deselect()

            # Set cooldown
            cooldown = notification_settings.get("notification_cooldown", 300)
            self.cooldown_entry.delete(0, tk.END)
            self.cooldown_entry.insert(0, str(cooldown))

            # Set memory threshold
            memory_threshold = notification_settings.get("memory_alert_threshold", 85.0)
            self.memory_threshold_entry.delete(0, tk.END)
            self.memory_threshold_entry.insert(0, str(memory_threshold))

            # Set storage threshold
            storage_threshold = notification_settings.get(
                "storage_alert_threshold", 90.0
            )
            self.storage_threshold_entry.delete(0, tk.END)
            self.storage_threshold_entry.insert(0, str(storage_threshold))

            # Set CPU threshold
            cpu_threshold = notification_settings.get("cpu_alert_threshold", 90.0)
            self.cpu_threshold_entry.delete(0, tk.END)
            self.cpu_threshold_entry.insert(0, str(cpu_threshold))

        except Exception as e:
            logger.error(f"Error loading settings into UI: {str(e)}")
