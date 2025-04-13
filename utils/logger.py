"""
Centralized logging module for consistent logging across the application.
"""

import datetime
import logging
from typing import Any, Callable


class Logger:
    """
    Centralized logging handler with UI integration.
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern to ensure only one logger exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the logger."""
        self.ui_callback = None

        # Set up Python's logging
        self.logger = logging.getLogger("automation_panel")
        self.logger.setLevel(logging.INFO)

        # File handler for persistent logs
        file_handler = logging.FileHandler("automation_panel.log")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(console_handler)

    def set_ui_callback(self, callback: Callable[[str], Any]):
        """Set the UI callback function for log display."""
        self.ui_callback = callback

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"

        # Log to Python's logging system
        if level == "INFO":
            self.logger.info(message)
        elif level == "WARNING":
            self.logger.warning(message)
        elif level == "ERROR":
            self.logger.error(message)
        elif level == "DEBUG":
            self.logger.debug(message)

        # Call UI callback if set
        if self.ui_callback:
            self.ui_callback(formatted_message)

    def info(self, message: str):
        """Log an info message."""
        self.log(message, "INFO")

    def warning(self, message: str):
        """Log a warning message."""
        self.log(message, "WARNING")

    def error(self, message: str):
        """Log an error message."""
        self.log(message, "ERROR")

    def debug(self, message: str):
        """Log a debug message."""
        self.log(message, "DEBUG")


# Create a singleton instance
logger = Logger()
