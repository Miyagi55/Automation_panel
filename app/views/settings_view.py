"""
Settings view for application settings and webdriver installation.
"""

import json
import os
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Any, Dict

import customtkinter as ctk

from app.utils.config import APP_CONFIG_PATH, DATA_DIR
from app.utils.logger import logger

from .base_view import BaseView


class SettingsView(BaseView):
    """
    View for application settings and webdriver installation.
    """

    def __init__(
        self, parent, controllers: Dict[str, Any], cache_refresh_callback=None
    ):
        """Initialize the settings view."""
        super().__init__(parent, controllers)
        self.cache_refresh_callback = cache_refresh_callback

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

        # Data directory settings
        data_dir_frame = ctk.CTkFrame(settings_frame)
        data_dir_frame.pack(fill="x", pady=(0, self.padding // 2))

        ctk.CTkLabel(data_dir_frame, text="Data Directory:").pack(side="left")
        self.data_dir_entry = ctk.CTkEntry(data_dir_frame, width=350)
        self.data_dir_entry.pack(side="left", padx=self.padding)
        self.data_dir_entry.insert(0, str(DATA_DIR))

        data_dir_browse_btn = ctk.CTkButton(
            data_dir_frame, text="Browse", command=self._browse_data_directory
        )
        data_dir_browse_btn.pack(side="left")

        data_dir_save_btn = ctk.CTkButton(
            data_dir_frame, text="Apply", command=self._save_data_directory
        )
        data_dir_save_btn.pack(side="left", padx=(self.padding // 2, 0))

        # Cache management settings
        cache_frame = ctk.CTkFrame(settings_frame)
        cache_frame.pack(fill="x", pady=(self.padding // 2, self.padding // 2))

        ctk.CTkLabel(cache_frame, text="Cache Management:").pack(side="left")

        # Cache toggle
        self.cache_enabled_var = ctk.BooleanVar(
            value=self.controllers["settings"].get_setting("cache_enabled")
        )
        cache_toggle = ctk.CTkSwitch(
            cache_frame,
            text="Enable Cache (disable to save context space)",
            variable=self.cache_enabled_var,
            command=self._toggle_cache,
        )
        cache_toggle.pack(side="left", padx=self.padding)

        # Cache info label
        cache_info_label = ctk.CTkLabel(
            cache_frame,
            text="ℹ️ Disabling cache saves space while keeping sessions persistent",
            font=("Segoe UI", 10),
            text_color="gray",
        )
        cache_info_label.pack(side="left", padx=(self.padding, 0))

        # Save settings button (This might be redundant now, consider removing or repurposing)
        # save_btn = ctk.CTkButton(
        #     settings_frame, text="Save General Settings", command=self._save_settings
        # )
        # save_btn.pack(anchor="e", pady=(self.padding, 0))

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
        self._load_current_data_directory()

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

    def _load_current_data_directory(self):
        """Load the current data directory from config.json"""
        self.data_dir_entry.delete(0, tk.END)
        self.data_dir_entry.insert(0, str(DATA_DIR))

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
                progress_win.after(1000, progress_win.destroy())  # Close after 1s
                self.download_btn.configure(state="normal")
                self._check_webdriver_status()

        # Install webdrivers in a separate thread
        self.controllers["browser"].install_webdrivers(update_progress)

    def _update_monitoring_interval(self):
        """Update the monitoring update interval."""
        # This should ideally be part of a general settings save mechanism
        try:
            interval = float(self.interval_entry.get())
            if interval < 0.1:
                raise ValueError("Interval must be at least 0.1 seconds.")

            # Example: Persist this setting if SettingsController is adapted for general settings
            # self.controllers["settings"].update_setting("monitoring_interval", interval)
            # self.controllers["settings"].save_settings() # If a general save mechanism exists

            self.controllers["monitoring"].set_update_interval(interval)
            messagebox.showinfo(
                "Success", f"Monitoring interval updated to {interval} seconds."
            )
        except ValueError as e:
            messagebox.showwarning("Input Error", f"Invalid interval: {str(e)}")

    def _browse_data_directory(self):
        """Browse for a data directory."""
        from tkinter import filedialog

        # Suggest the current DATA_DIR's parent or DATA_DIR itself as initial directory
        initial_dir = str(DATA_DIR.parent if DATA_DIR else Path.home())
        directory = filedialog.askdirectory(initialdir=initial_dir)
        if directory:
            self.data_dir_entry.delete(0, tk.END)
            self.data_dir_entry.insert(0, directory)

    def _save_data_directory(self):
        """Save the data directory to config.json."""
        new_data_dir_str = self.data_dir_entry.get()

        if not new_data_dir_str:
            messagebox.showwarning("Input Error", "Data directory cannot be empty.")
            return

        try:
            new_data_dir = Path(new_data_dir_str)
            # Ensure the path is absolute
            if not new_data_dir.is_absolute():
                messagebox.showwarning(
                    "Input Error",
                    "Please provide an absolute path for the data directory.",
                )
                return

            os.makedirs(new_data_dir, exist_ok=True)  # Create if it doesn't exist

            config_path = APP_CONFIG_PATH  # Use the centrally defined config path

            current_config = {}
            if config_path.exists():
                with open(config_path, "r") as f:
                    current_config = json.load(f)

            current_config["data_dir"] = str(new_data_dir)  # Store as string

            with open(config_path, "w") as f:
                json.dump(current_config, f, indent=4)

            messagebox.showinfo(
                "Success",
                "Data directory updated. Please restart the application for changes to take full effect.",
            )
            logger.info(f"Data directory updated to: {new_data_dir_str}")
            # Update DATA_DIR in memory for the current session if possible/needed, or rely on restart
            # For now, we rely on restart as indicated to the user.
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update data directory: {str(e)}")
            logger.error(f"Failed to update data directory: {str(e)}")

    # def _save_settings(self):
    #     """Save all general settings."""
    #     # This method would handle saving other settings like monitoring interval, concurrency, etc.
    #     # to a general settings store (e.g., could also be config.json or a separate file)
    #     # For now, it's commented out as we primarily focused on data_dir
    #     try:
    #         # Example: Save monitoring interval
    #         interval = float(self.interval_entry.get())
    #         self.controllers["settings"].update_setting("monitoring_interval", interval)

    #         # Example: Save browser concurrency
    #         concurrency = int(self.concurrency_entry.get())
    #         self.controllers["settings"].update_setting("browser_concurrency", concurrency)

    #         # Persist all settings
    #         self.controllers["settings"].save_settings() # Assuming this saves to the config file

    #         messagebox.showinfo("Settings", "General settings saved successfully.")
    #         logger.info("Application general settings updated.")
    #     except ValueError as e:
    #         messagebox.showwarning("Input Error", f"Invalid setting value: {str(e)}")
    #     except Exception as e:
    #         messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

    def _toggle_cache(self):
        """Toggle the cache enabled setting."""
        try:
            cache_enabled = self.cache_enabled_var.get()
            self.controllers["settings"].update_setting("cache_enabled", cache_enabled)

            # Show feedback to user
            if cache_enabled:
                logger.info("Cache enabled - full cache management available")
            else:
                logger.info(
                    "Cache disabled - space saving mode activated, sessions remain persistent"
                )

            # Refresh cache view if callback is available
            if self.cache_refresh_callback:
                self.cache_refresh_callback()

        except Exception as e:
            logger.error(f"Failed to toggle cache setting: {str(e)}")
