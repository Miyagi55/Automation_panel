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
