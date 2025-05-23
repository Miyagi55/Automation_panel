"""
Cache Management View for the Automation Panel.
Provides UI for managing browser context cache without losing sessions.
"""

import threading
from typing import Any, Dict

import customtkinter as ctk

from app.utils.logger import logger


class CacheView:
    """
    View for managing browser context cache.
    Provides interface for analyzing and clearing cache while preserving sessions.
    """

    def __init__(self, parent_frame, controllers: Dict[str, Any]):
        """
        Initialize the cache view.

        Args:
            parent_frame: Parent frame for this view
            controllers: Dictionary of controllers
        """
        self.parent_frame = parent_frame
        self.controllers = controllers
        self.browser_controller = controllers.get("browser")

        # Create main frame
        self.main_frame = ctk.CTkFrame(parent_frame)

        # UI components
        self.cache_stats_frame = None
        self.cache_operations_frame = None
        self.progress_frame = None
        self.log_frame = None

        # Cache statistics
        self.current_stats = {}

        # Setup UI
        self.setup_ui()

        # Initial load
        self.refresh_cache_stats()

    def setup_ui(self):
        """Set up the cache management user interface."""
        # Title
        title_label = ctk.CTkLabel(
            self.main_frame,
            text="Browser Cache Management",
            font=("Segoe UI", 20, "bold"),
        )
        title_label.pack(pady=(20, 10), padx=20, anchor="w")

        # Description
        desc_label = ctk.CTkLabel(
            self.main_frame,
            text="Manage browser context cache to free up disk space while preserving login sessions.",
            font=("Segoe UI", 12),
            text_color="gray",
        )
        desc_label.pack(pady=(0, 20), padx=20, anchor="w")

        # Cache Statistics Frame
        self.setup_cache_stats_frame()

        # Cache Operations Frame
        self.setup_cache_operations_frame()

        # Progress Frame
        self.setup_progress_frame()

        # Log Frame
        self.setup_log_frame()

    def setup_cache_stats_frame(self):
        """Set up the cache statistics display frame."""
        self.cache_stats_frame = ctk.CTkFrame(self.main_frame)
        self.cache_stats_frame.pack(pady=10, padx=20, fill="x")

        # Stats title
        stats_title = ctk.CTkLabel(
            self.cache_stats_frame,
            text="Cache Statistics",
            font=("Segoe UI", 16, "bold"),
        )
        stats_title.pack(pady=(15, 10), padx=15, anchor="w")

        # Stats content frame
        self.stats_content_frame = ctk.CTkFrame(self.cache_stats_frame)
        self.stats_content_frame.pack(pady=(0, 15), padx=15, fill="x")

        # Initial stats labels
        self.total_sessions_label = ctk.CTkLabel(
            self.stats_content_frame, text="Total Sessions: Loading..."
        )
        self.total_sessions_label.pack(pady=5, padx=15, anchor="w")

        self.total_size_label = ctk.CTkLabel(
            self.stats_content_frame, text="Total Size: Loading..."
        )
        self.total_size_label.pack(pady=5, padx=15, anchor="w")

        self.clearable_size_label = ctk.CTkLabel(
            self.stats_content_frame, text="Clearable Cache: Loading..."
        )
        self.clearable_size_label.pack(pady=5, padx=15, anchor="w")

        self.preserved_size_label = ctk.CTkLabel(
            self.stats_content_frame, text="Preserved Data: Loading..."
        )
        self.preserved_size_label.pack(pady=5, padx=15, anchor="w")

        # Refresh button
        refresh_btn = ctk.CTkButton(
            self.cache_stats_frame,
            text="Refresh Statistics",
            command=self.refresh_cache_stats,
        )
        refresh_btn.pack(pady=(0, 15), padx=15, anchor="e")

    def setup_cache_operations_frame(self):
        """Set up the cache operations frame."""
        self.cache_operations_frame = ctk.CTkFrame(self.main_frame)
        self.cache_operations_frame.pack(pady=10, padx=20, fill="x")

        # Operations title
        ops_title = ctk.CTkLabel(
            self.cache_operations_frame,
            text="Cache Operations",
            font=("Segoe UI", 16, "bold"),
        )
        ops_title.pack(pady=(15, 10), padx=15, anchor="w")

        # Backup option
        self.backup_var = ctk.BooleanVar(value=True)
        backup_checkbox = ctk.CTkCheckBox(
            self.cache_operations_frame,
            text="Create backup before clearing cache (optional)",
            variable=self.backup_var,
        )
        backup_checkbox.pack(pady=5, padx=15, anchor="w")

        # Warning label
        warning_label = ctk.CTkLabel(
            self.cache_operations_frame,
            text="⚠️ This will clear browser cache while preserving login sessions and user data.",
            font=("Segoe UI", 11),
            text_color="orange",
        )
        warning_label.pack(pady=(10, 5), padx=15, anchor="w")

        # Buttons frame
        buttons_frame = ctk.CTkFrame(self.cache_operations_frame)
        buttons_frame.pack(pady=(10, 15), padx=15, fill="x")

        # Clear all cache button
        self.clear_all_btn = ctk.CTkButton(
            buttons_frame,
            text="Clear All Sessions Cache",
            command=self.clear_all_cache,
            fg_color="red",
            hover_color="darkred",
        )
        self.clear_all_btn.pack(side="left", padx=(0, 10))

        # Analyze button
        analyze_btn = ctk.CTkButton(
            buttons_frame, text="Analyze Cache", command=self.analyze_cache
        )
        analyze_btn.pack(side="left", padx=(0, 10))

        # Account-specific operations frame
        account_frame = ctk.CTkFrame(self.cache_operations_frame)
        account_frame.pack(pady=(10, 15), padx=15, fill="x")

        account_label = ctk.CTkLabel(account_frame, text="Account-specific operations:")
        account_label.pack(pady=(10, 5), padx=15, anchor="w")

        # Account ID entry
        account_entry_frame = ctk.CTkFrame(account_frame)
        account_entry_frame.pack(pady=5, padx=15, fill="x")

        ctk.CTkLabel(account_entry_frame, text="Account ID:").pack(
            side="left", padx=(10, 5)
        )

        self.account_id_entry = ctk.CTkEntry(
            account_entry_frame, placeholder_text="e.g., 001"
        )
        self.account_id_entry.pack(side="left", padx=5, fill="x", expand=True)

        clear_account_btn = ctk.CTkButton(
            account_entry_frame,
            text="Clear Account Cache",
            command=self.clear_account_cache,
            width=150,
        )
        clear_account_btn.pack(side="right", padx=(5, 10))

    def setup_progress_frame(self):
        """Set up the progress display frame."""
        self.progress_frame = ctk.CTkFrame(self.main_frame)
        self.progress_frame.pack(pady=10, padx=20, fill="x")

        # Progress title
        progress_title = ctk.CTkLabel(
            self.progress_frame,
            text="Operation Progress",
            font=("Segoe UI", 16, "bold"),
        )
        progress_title.pack(pady=(15, 10), padx=15, anchor="w")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(pady=5, padx=15, fill="x")
        self.progress_bar.set(0)

        # Progress label
        self.progress_label = ctk.CTkLabel(
            self.progress_frame, text="Ready", font=("Segoe UI", 11)
        )
        self.progress_label.pack(pady=(5, 15), padx=15, anchor="w")

    def setup_log_frame(self):
        """Set up the log display frame."""
        self.log_frame = ctk.CTkFrame(self.main_frame)
        self.log_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Log title
        log_title = ctk.CTkLabel(
            self.log_frame, text="Operation Log", font=("Segoe UI", 16, "bold")
        )
        log_title.pack(pady=(15, 10), padx=15, anchor="w")

        # Log text area
        self.log_text = ctk.CTkTextbox(self.log_frame, height=200)
        self.log_text.pack(pady=(0, 15), padx=15, fill="both", expand=True)

        # Clear log button
        clear_log_btn = ctk.CTkButton(
            self.log_frame, text="Clear Log", command=self.clear_log, width=100
        )
        clear_log_btn.pack(pady=(0, 15), padx=15, anchor="e")

    def refresh_cache_stats(self):
        """Refresh cache statistics display."""

        def refresh_thread():
            try:
                self.update_progress("Loading cache statistics...", 0.3)

                if not self.browser_controller:
                    self.log_message("❌ Browser controller not available")
                    return

                stats = self.browser_controller.get_cache_stats()

                if stats.get("error"):
                    self.log_message(f"❌ Error loading stats: {stats['error']}")
                    return

                self.current_stats = stats
                self.update_stats_display(stats)
                self.update_progress("Statistics loaded successfully", 1.0)
                self.log_message("✅ Cache statistics refreshed")

            except Exception as e:
                error_msg = f"Failed to refresh cache statistics: {str(e)}"
                self.log_message(f"❌ {error_msg}")
                logger.error(error_msg)
            finally:
                # Reset progress after a delay
                self.main_frame.after(2000, lambda: self.update_progress("Ready", 0))

        thread = threading.Thread(target=refresh_thread, daemon=True)
        thread.start()

    def update_stats_display(self, stats: Dict[str, Any]):
        """Update the statistics display with new data."""

        def update_ui():
            total_sessions = stats.get("total_sessions", 0)
            total_size_mb = stats.get("total_size_mb", 0)
            clearable_size_mb = stats.get("total_clearable_size_mb", 0)
            preserved_size_mb = stats.get("total_preserved_size_mb", 0)

            self.total_sessions_label.configure(
                text=f"Total Sessions: {total_sessions}"
            )
            self.total_size_label.configure(text=f"Total Size: {total_size_mb:.2f} MB")
            self.clearable_size_label.configure(
                text=f"Clearable Cache: {clearable_size_mb:.2f} MB"
            )
            self.preserved_size_label.configure(
                text=f"Preserved Data: {preserved_size_mb:.2f} MB"
            )

        self.main_frame.after(0, update_ui)

    def clear_all_cache(self):
        """Clear cache for all sessions."""
        if not self.browser_controller:
            self.log_message("❌ Browser controller not available")
            return

        # Confirmation dialog
        result = ctk.CTkInputDialog(
            text="Type 'CONFIRM' to clear cache for all sessions:",
            title="Confirm Cache Clearing",
        ).get_input()

        if result != "CONFIRM":
            self.log_message("⚠️ Cache clearing cancelled")
            return

        backup = self.backup_var.get()
        self.log_message(
            f"🚀 Starting cache clearing for all sessions (backup: {backup})"
        )

        self.browser_controller.clear_cache_async(
            account_id=None, backup=backup, progress_callback=self.update_cache_progress
        )

    def clear_account_cache(self):
        """Clear cache for a specific account."""
        if not self.browser_controller:
            self.log_message("❌ Browser controller not available")
            return

        account_id = self.account_id_entry.get().strip()
        if not account_id:
            self.log_message("⚠️ Please enter an account ID")
            return

        backup = self.backup_var.get()
        self.log_message(
            f"🚀 Starting cache clearing for account {account_id} (backup: {backup})"
        )

        self.browser_controller.clear_cache_async(
            account_id=account_id,
            backup=backup,
            progress_callback=self.update_cache_progress,
        )

    def analyze_cache(self):
        """Analyze cache usage and display detailed information."""

        def analyze_thread():
            try:
                self.update_progress("Analyzing cache usage...", 0.5)

                if not self.browser_controller:
                    self.log_message("❌ Browser controller not available")
                    return

                stats = self.browser_controller.analyze_cache()

                if stats.get("error"):
                    self.log_message(f"❌ Analysis error: {stats['error']}")
                    return

                self.log_message("📊 Cache Analysis Results:")
                self.log_message(f"   Total Sessions: {stats.get('total_sessions', 0)}")
                self.log_message(
                    f"   Total Size: {stats.get('total_size_mb', 0):.2f} MB"
                )
                self.log_message(
                    f"   Clearable: {stats.get('total_clearable_size_mb', 0):.2f} MB"
                )
                self.log_message(
                    f"   Preserved: {stats.get('total_preserved_size_mb', 0):.2f} MB"
                )

                # Show per-session breakdown
                sessions = stats.get("sessions", [])
                if sessions:
                    self.log_message("   Per-session breakdown:")
                    for session in sessions[:10]:  # Show first 10 sessions
                        name = session.get("name", "Unknown")
                        clearable = session.get("clearable_size_mb", 0)
                        self.log_message(f"     {name}: {clearable:.2f} MB clearable")

                    if len(sessions) > 10:
                        self.log_message(
                            f"     ... and {len(sessions) - 10} more sessions"
                        )

                self.update_progress("Analysis complete", 1.0)

            except Exception as e:
                error_msg = f"Cache analysis failed: {str(e)}"
                self.log_message(f"❌ {error_msg}")
                logger.error(error_msg)
            finally:
                self.main_frame.after(2000, lambda: self.update_progress("Ready", 0))

        thread = threading.Thread(target=analyze_thread, daemon=True)
        thread.start()

    def update_cache_progress(self, message: str):
        """Update progress from cache operations."""
        self.log_message(f"📋 {message}")

        # Update progress bar based on message
        if "Starting" in message:
            self.update_progress(message, 0.1)
        elif "clearing" in message.lower() or "freed" in message.lower():
            self.update_progress(message, 0.9)
        elif "completed" in message.lower() or "failed" in message.lower():
            self.update_progress(message, 1.0)
            # Refresh stats after completion
            self.main_frame.after(1000, self.refresh_cache_stats)
            # Reset progress after delay
            self.main_frame.after(3000, lambda: self.update_progress("Ready", 0))

    def update_progress(self, message: str, progress: float):
        """Update the progress bar and label."""

        def update_ui():
            self.progress_bar.set(progress)
            self.progress_label.configure(text=message)

        self.main_frame.after(0, update_ui)

    def log_message(self, message: str):
        """Add a message to the log display."""

        def update_log():
            self.log_text.insert("end", f"{message}\n")
            self.log_text.see("end")

        self.main_frame.after(0, update_log)

    def clear_log(self):
        """Clear the log display."""
        self.log_text.delete("1.0", "end")

    def show(self):
        """Show this view."""
        self.main_frame.pack(fill="both", expand=True)

    def hide(self):
        """Hide this view."""
        self.main_frame.pack_forget()

    def refresh(self):
        """Refresh the view data."""
        self.refresh_cache_stats()
