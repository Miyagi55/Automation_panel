"""
Facebook Automation Panel - Main Application

This application provides a graphical interface for Facebook automation tasks.
It uses an MVC architecture to separate concerns and promote maintainability.
"""

import argparse

import customtkinter as ctk

# Import controllers
from controllers.account_controller import AccountController
from controllers.automation_controller import AutomationController
from controllers.browser_controller import BrowserController
from controllers.monitoring_controller import MonitoringController
from controllers.settings_controller import SettingsController

# Import logger
from utils.logger import logger

# Import views
from views.account_view import AccountView
from views.automation_view import AutomationView
from views.monitoring_view import MonitoringView
from views.settings_view import SettingsView

# Set appearance mode and theme
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class SocialMediaAutomationApp(ctk.CTk):
    """
    Main application class that coordinates all components.
    """

    def __init__(self):
        """Initialize the application."""
        super().__init__()
        self.title("Facebook Automation Panel")
        self.geometry("1000x700")
        self.resizable(True, True)

        self.setup_controllers()
        self.setup_gui()
        self.setup_views()
        logger.info("Application initialized")

    def setup_gui(self):
        """Set up the GUI framework."""
        # Create main frames
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.pack(side="left", fill="y", expand=False)

        self.content_frame = ctk.CTkFrame(self, corner_radius=0)
        self.content_frame.pack(side="right", fill="both", expand=True)

    def setup_controllers(self):
        """Set up the controllers."""
        # Create the controllers
        self.browser_controller = BrowserController()
        self.account_controller = AccountController(
            update_ui_callback=self.refresh_account_view
        )
        self.monitoring_controller = MonitoringController(
            update_callback=self.update_resource_display
        )
        self.automation_controller = AutomationController(
            update_ui_callback=self.refresh_workflow_view,
            progress_callback=self.update_workflow_progress,
        )
        self.settings_controller = SettingsController()

        # Store controllers in a dictionary for easy access
        self.controllers = {
            "account": self.account_controller,
            "automation": self.automation_controller,
            "monitoring": self.monitoring_controller,
            "browser": self.browser_controller,
            "settings": self.settings_controller,
        }

        # Start monitoring
        self.monitoring_controller.start_monitoring()

    def setup_views(self):
        """Set up the views."""
        # Set up logger UI callback
        logger.set_ui_callback(self.log_to_ui)

        # Create views
        self.views = {
            "accounts": AccountView(self.content_frame, self.controllers),
            "automation": AutomationView(self.content_frame, self.controllers),
            "monitoring": MonitoringView(self.content_frame, self.controllers),
            "settings": SettingsView(self.content_frame, self.controllers),
        }

        # Add sidebar buttons
        self.setup_sidebar()

        # Set the initial view
        self.show_section("accounts")

    def setup_sidebar(self):
        """Set up the sidebar navigation."""
        title_label = ctk.CTkLabel(
            self.sidebar_frame, text="Automation Panel", font=("Segoe UI", 18, "bold")
        )
        title_label.pack(pady=(16, 0), padx=16, anchor="w")

        buttons = [
            ("Accounts", lambda: self.show_section("accounts")),
            ("Automation", lambda: self.show_section("automation")),
            ("Monitoring", lambda: self.show_section("monitoring")),
            ("Settings", lambda: self.show_section("settings")),
        ]
        for btn_text, cmd in buttons:
            btn = ctk.CTkButton(self.sidebar_frame, text=btn_text, command=cmd)
            btn.pack(pady=8, padx=16, fill="x")

        self.theme_switch = ctk.CTkSwitch(
            self.sidebar_frame,
            text="Dark Mode",
            command=self.toggle_theme,
            onvalue="Dark",
            offvalue="Light",
        )
        self.theme_switch.pack(pady=16, padx=16, side="bottom")

    def show_section(self, section_name: str):
        """Show the selected section."""
        # Hide all views
        for view in self.views.values():
            view.hide()

        # Show and refresh the selected view
        if section_name in self.views:
            # First show the view
            self.views[section_name].show()

            try:
                # Then refresh - wrapped in try block to handle initial load issues
                if section_name == "accounts":
                    self.views[section_name].refresh()
            except Exception as e:
                logger.error(f"Error refreshing {section_name} view: {str(e)}")

            logger.info(f"Showing {section_name} section")

    def toggle_theme(self):
        """Toggle between light and dark themes."""
        mode = self.theme_switch.get()
        ctk.set_appearance_mode(mode)
        logger.info(f"Theme switched to {mode} mode")

    def refresh_account_view(self):
        """Refresh the account view."""
        if "accounts" in self.views:
            self.views["accounts"].refresh()

    def refresh_workflow_view(self):
        """Refresh the workflow view."""
        if "automation" in self.views:
            self.views["automation"].refresh()

    def update_resource_display(self, resource_data):
        """Update the resource display with new data."""
        if "monitoring" in self.views:
            self.views["monitoring"].update_resources(resource_data)

    def update_workflow_progress(self, workflow_name, progress):
        """Update the workflow progress display."""
        if "automation" in self.views:
            self.views["automation"].update_workflow_progress(workflow_name, progress)

    def log_to_ui(self, message):
        """Log a message to the UI."""
        try:
            if "monitoring" in self.views:
                self.views["monitoring"].add_log(message)
            else:
                print(message)  # Fallback to console
        except Exception as e:
            print(f"Error logging to UI: {str(e)}")
            print(message)  # Ensure message is still displayed


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Facebook Automation Panel")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()

    # Set up logging
    if args.debug:
        logger.debug("Debug mode enabled")

    # Start the application
    app = SocialMediaAutomationApp()
    app.mainloop()
