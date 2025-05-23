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

    def __init__(
        self, parent_frame, controllers: Dict[str, Any], navigation_callback=None
    ):
        """
        Initialize the cache view.

        Args:
            parent_frame: Parent frame for this view
            controllers: Dictionary of controllers
            navigation_callback: Optional callback for navigation between sections
        """
        self.parent_frame = parent_frame
        self.controllers = controllers
        self.browser_controller = controllers.get("browser")
        self.settings_controller = controllers.get("settings")
        self.navigation_callback = navigation_callback

        # Store reference to parent app for navigation (if available)
        self.parent_app = getattr(parent_frame, "master", None)

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

        # Check if cache is enabled
        cache_enabled = True
        if self.settings_controller:
            cache_enabled = self.settings_controller.get_setting("cache_enabled")

        if not cache_enabled:
            # Show cache disabled message
            disabled_frame = ctk.CTkFrame(self.main_frame)
            disabled_frame.pack(pady=20, padx=20, fill="both", expand=True)

            disabled_title = ctk.CTkLabel(
                disabled_frame,
                text="🚫 Cache Management Disabled",
                font=("Segoe UI", 18, "bold"),
            )
            disabled_title.pack(pady=(20, 10))

            disabled_desc = ctk.CTkLabel(
                disabled_frame,
                text="Cache management is currently disabled to save context space.\n"
                "Sessions remain persistent and functional.\n\n"
                "To enable cache management, go to Settings and toggle 'Enable Cache'.",
                font=("Segoe UI", 12),
                text_color="gray",
                justify="center",
            )
            disabled_desc.pack(pady=10)

            settings_btn = ctk.CTkButton(
                disabled_frame,
                text="Go to Settings",
                command=lambda: self._navigate_to_settings(),
            )
            settings_btn.pack(pady=20)

            return

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
            text="Storage Usage Statistics",
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
            self.stats_content_frame, text="Total Storage Usage: Loading..."
        )
        self.total_size_label.pack(pady=5, padx=15, anchor="w")

        self.clearable_size_label = ctk.CTkLabel(
            self.stats_content_frame, text="Clearable Cache: Loading..."
        )
        self.clearable_size_label.pack(pady=5, padx=15, anchor="w")

        self.preserved_size_label = ctk.CTkLabel(
            self.stats_content_frame, text="Preserved Session Data: Loading..."
        )
        self.preserved_size_label.pack(pady=5, padx=15, anchor="w")

        # Add new labels for enhanced information
        self.other_size_label = ctk.CTkLabel(
            self.stats_content_frame, text="Other Data: Loading..."
        )
        self.other_size_label.pack(pady=5, padx=15, anchor="w")

        self.storage_efficiency_label = ctk.CTkLabel(
            self.stats_content_frame, text="Storage Analysis: Loading..."
        )
        self.storage_efficiency_label.pack(pady=5, padx=15, anchor="w")

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
        self.backup_var = ctk.BooleanVar(value=False)
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
                self.update_progress("Initializing cache analysis...", 0.1)

                if not self.browser_controller:
                    self.log_message("❌ Browser controller not available")
                    self.update_progress("Error: Browser controller unavailable", 0)
                    return

                self.update_progress("Scanning browser sessions...", 0.3)

                # Get cache statistics
                stats = self.browser_controller.get_cache_stats()

                if stats.get("error"):
                    error_msg = f"❌ Error loading stats: {stats['error']}"
                    self.log_message(error_msg)
                    self.update_progress("Error loading statistics", 0)

                    # Show error details to help debugging
                    if "not found" in str(stats["error"]).lower():
                        self.log_message(
                            "💡 Tip: Ensure browser sessions directory exists"
                        )
                    elif "permission" in str(stats["error"]).lower():
                        self.log_message(
                            "💡 Tip: Check file permissions on browser session directories"
                        )
                    return

                self.update_progress("Processing storage analysis...", 0.7)

                # Validate statistics data
                if not isinstance(stats, dict):
                    self.log_message("❌ Invalid statistics data received")
                    self.update_progress("Error: Invalid data format", 0)
                    return

                # Store current stats for potential later use
                self.current_stats = stats

                # Extract key metrics for logging
                total_sessions = stats.get("total_sessions", 0)
                total_size_mb = stats.get("total_size_mb", 0)
                clearable_size_mb = stats.get("total_clearable_size_mb", 0)

                self.update_progress("Updating display...", 0.9)

                # Update the display
                self.update_stats_display(stats)

                # Log success with details
                success_msg = "✅ Cache statistics refreshed successfully"
                self.log_message(success_msg)
                self.log_message(
                    f"   📊 Found {total_sessions} sessions using {total_size_mb:.1f} MB total"
                )

                if clearable_size_mb > 0:
                    self.log_message(f"   🗑️  {clearable_size_mb:.1f} MB can be cleared")
                else:
                    self.log_message("   ✨ No cache data to clear")

                # Show analysis type
                analysis_type = stats.get("analysis_type", "unknown")
                self.log_message(f"   📈 Analysis type: {analysis_type}")

                self.update_progress("Analysis complete ✅", 1.0)

            except Exception as e:
                error_msg = f"Failed to refresh cache statistics: {str(e)}"
                self.log_message(f"❌ {error_msg}")
                logger.error(error_msg)

                # Provide helpful debugging information
                self.log_message("🔧 Debug information:")
                self.log_message(f"   - Error type: {type(e).__name__}")
                self.log_message(
                    f"   - Browser controller available: {self.browser_controller is not None}"
                )

                # Show generic error state
                if hasattr(self, "storage_efficiency_label"):

                    def show_error():
                        self.storage_efficiency_label.configure(
                            text="⚠️ Error refreshing statistics - check logs"
                        )

                    self.main_frame.after(0, show_error)

                self.update_progress("Error occurred during refresh", 0)

            finally:
                # Reset progress after a delay
                self.main_frame.after(3000, lambda: self.update_progress("Ready", 0))

        # Show loading state immediately
        self.update_progress("Starting refresh...", 0.05)

        # Start refresh in background thread
        thread = threading.Thread(target=refresh_thread, daemon=True)
        thread.start()

    def update_stats_display(self, stats: Dict[str, Any]):
        """Update the statistics display with new data."""

        def update_ui():
            try:
                total_sessions = stats.get("total_sessions", 0)
                total_size_mb = stats.get("total_size_mb", 0)
                clearable_size_mb = stats.get("total_clearable_size_mb", 0)
                preserved_size_mb = stats.get("total_preserved_size_mb", 0)
                other_size_mb = stats.get("total_other_size_mb", 0)

                # Get percentages for better understanding
                clearable_pct = stats.get("clearable_percentage", 0)
                preserved_pct = stats.get("preserved_percentage", 0)
                other_pct = stats.get("other_percentage", 0)

                # Check if this is using enhanced analysis
                analysis_type = stats.get("analysis_type", "basic")

                # Update session count with better formatting
                session_text = f"Total Sessions: {total_sessions}"
                if total_sessions == 0:
                    session_text += " (No browser sessions found)"
                elif total_sessions == 1:
                    session_text += " (1 active session)"
                else:
                    session_text += f" ({total_sessions} active sessions)"

                self.total_sessions_label.configure(text=session_text)

                # Enhanced total storage display
                total_text = f"Total Storage Usage: {total_size_mb:.2f} MB"
                if total_size_mb > 1024:
                    total_gb = total_size_mb / 1024
                    total_text += f" ({total_gb:.2f} GB)"
                self.total_size_label.configure(text=total_text)

                # Enhanced clearable cache display
                clearable_text = f"Clearable Cache: {clearable_size_mb:.2f} MB ({clearable_pct:.1f}%)"
                if clearable_size_mb == 0:
                    clearable_text += " (Cache may be disabled or already cleared)"
                elif clearable_size_mb > 100:
                    clearable_text += " ⚠️ Consider clearing"
                self.clearable_size_label.configure(text=clearable_text)

                # Enhanced preserved data display
                preserved_text = f"Preserved Session Data: {preserved_size_mb:.2f} MB ({preserved_pct:.1f}%)"
                if preserved_size_mb > 0:
                    preserved_text += " (Contains login sessions, cookies, etc.)"
                self.preserved_size_label.configure(text=preserved_text)

                # Update the other data label with better information
                if hasattr(self, "other_size_label"):
                    other_text = (
                        f"Other Data: {other_size_mb:.2f} MB ({other_pct:.1f}%)"
                    )
                    if other_size_mb > 0:
                        other_text += " (Unclassified browser data)"
                    self.other_size_label.configure(text=other_text)

                # Enhanced storage efficiency information
                if hasattr(self, "storage_efficiency_label"):
                    if total_size_mb > 0:
                        efficiency_text = f"Storage Analysis: {analysis_type.capitalize()} scan complete"

                        # Add actionable insights
                        if clearable_size_mb > 50:
                            efficiency_text += (
                                f" • {clearable_size_mb:.1f} MB can be cleared"
                            )
                        elif clearable_size_mb > 0:
                            efficiency_text += (
                                f" • {clearable_size_mb:.1f} MB available to clear"
                            )
                        else:
                            efficiency_text += " • No cache to clear"

                        # Add storage efficiency rating
                        efficiency_ratio = (
                            clearable_size_mb / total_size_mb
                            if total_size_mb > 0
                            else 0
                        )
                        if efficiency_ratio > 0.5:
                            efficiency_text += (
                                " (High cache usage - recommended to clear)"
                            )
                        elif efficiency_ratio > 0.2:
                            efficiency_text += " (Moderate cache usage)"
                        else:
                            efficiency_text += " (Low cache usage - optimal)"
                    else:
                        efficiency_text = "Storage Analysis: No browser data found"

                    self.storage_efficiency_label.configure(text=efficiency_text)

                # Log successful update
                logger.info(
                    f"Statistics updated: {total_sessions} sessions, {total_size_mb:.2f} MB total"
                )

            except Exception as e:
                error_msg = f"Failed to update statistics display: {str(e)}"
                logger.error(error_msg)
                # Show error in UI
                if hasattr(self, "storage_efficiency_label"):
                    self.storage_efficiency_label.configure(
                        text="⚠️ Error updating statistics display"
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

    def refresh(self):
        """
        Refresh the cache view.
        Called when the view is activated or when external triggers require refresh.
        """
        try:
            # Clear any existing logs when refreshing the view
            self.log_message("🔄 Refreshing cache management view...")

            # Immediately refresh statistics
            self.refresh_cache_stats()

            logger.info("Cache view refreshed successfully")

        except Exception as e:
            error_msg = f"Failed to refresh cache view: {str(e)}"
            self.log_message(f"❌ {error_msg}")
            logger.error(error_msg)

    def show(self):
        """Show this view and refresh data."""
        self.main_frame.pack(fill="both", expand=True)
        # Auto-refresh when showing the view for better user experience
        self.main_frame.after(100, self.refresh_cache_stats)

    def hide(self):
        """Hide this view."""
        self.main_frame.pack_forget()

    def get_current_stats(self) -> Dict[str, Any]:
        """
        Get the current cached statistics.

        Returns:
            Dictionary containing current statistics or empty dict if none available
        """
        return getattr(self, "current_stats", {})

    def _navigate_to_settings(self):
        """Navigate to the settings view."""
        if self.navigation_callback:
            self.navigation_callback("settings")
            logger.info("Navigated to settings")
        else:
            logger.info(
                "Navigation callback not available - please go to Settings manually"
            )
