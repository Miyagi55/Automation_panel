"""
Base view class providing common functionality for all views.
"""

from typing import Any, Callable, Dict, Optional

import customtkinter as ctk


class BaseView(ctk.CTkFrame):
    """
    Base class for all views in the application.
    Provides common functionality and consistent styling.
    """

    def __init__(self, parent, controllers: Dict[str, Any], **kwargs):
        """
        Initialize the base view.

        Args:
            parent: The parent widget
            controllers: Dictionary of controllers this view can access
            **kwargs: Additional arguments to pass to CTkFrame
        """
        super().__init__(parent, **kwargs)
        self.controllers = controllers
        self.padding = 16
        self.setup_ui()

    def setup_ui(self):
        """
        Set up the UI components.
        Should be overridden by subclasses.
        """
        pass

    def refresh(self):
        """
        Refresh the view's content.
        Should be overridden by subclasses.
        """
        pass

    def show(self):
        """Show this view."""
        self.pack(fill="both", expand=True)
        self.refresh()

    def hide(self):
        """Hide this view."""
        self.pack_forget()

    def create_header(self, title: str):
        """Create a header with the given title."""
        header = ctk.CTkLabel(self, text=title, font=("Segoe UI", 16, "bold"))
        header.pack(pady=(self.padding, 0), padx=self.padding, anchor="w")
        return header

    def create_button(
        self,
        text: str,
        command: Callable,
        fg_color: Optional[str] = None,
        hover_color: Optional[str] = None,
    ):
        """Create a button with the given text and command."""
        return ctk.CTkButton(
            self, text=text, command=command, fg_color=fg_color, hover_color=hover_color
        )
