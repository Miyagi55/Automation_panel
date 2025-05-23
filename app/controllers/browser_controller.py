"""
Browser controller to manage Playwright browser functionality.
"""

import threading
from typing import Any, Callable, Dict, Optional

from app.models.playwright.browser_manager import BrowserManager
from app.models.playwright.cache_manager import BrowserCacheManager
from app.utils.logger import logger


class BrowserController:
    """
    Controller for browser operations.
    Manages browser installation, configuration, and cache management.
    """

    def __init__(self):
        """Initialize the browser controller."""
        self.browser_manager = BrowserManager()
        self.cache_manager = BrowserCacheManager()

    def get_webdriver_path(self) -> Optional[str]:
        """Get the current webdriver path."""
        return self.browser_manager.webdriver_path

    def install_webdrivers(self, update_progress: Callable[[str, float], None]) -> None:
        """
        Install Playwright webdrivers.

        Args:
            update_progress: Callback for progress updates
        """

        def install_thread():
            """Run installation in a separate thread."""
            success = self.browser_manager.install_webdrivers(
                logger.info, update_progress
            )
            if success:
                logger.info("Webdrivers installed successfully")
            else:
                logger.error("Failed to install webdrivers")

        # Start installation in a thread to keep UI responsive
        install_thread = threading.Thread(target=install_thread)
        install_thread.daemon = True
        install_thread.start()

    def get_chromium_executable(self) -> Optional[str]:
        """Get the path to the Chromium executable."""
        return self.browser_manager.get_chromium_executable(logger.info)

    def verify_installation(self) -> bool:
        """Verify the webdriver installation."""
        return self.browser_manager.webdriver_path is not None

    def get_session_dir(self, account_id: str) -> str:
        """
        Get the session directory for a given account ID.

        Args:
            account_id: The account ID

        Returns:
            Path to the session directory
        """
        return self.browser_manager.get_session_dir(account_id)

    # Cache Management Methods

    def analyze_cache(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze cache usage for a specific account or all accounts.

        Args:
            account_id: Account ID to analyze (if None, analyzes all accounts)

        Returns:
            Dictionary containing cache analysis results
        """
        try:
            if account_id:
                session_dir = self.get_session_dir(account_id)
                return self.cache_manager.analyze_session_cache(session_dir)
            else:
                sessions_base_dir = self.browser_manager._sessions_base_dir
                return self.cache_manager.get_cache_statistics(sessions_base_dir)
        except Exception as e:
            logger.error(f"Cache analysis failed: {str(e)}")
            return {"error": f"Cache analysis failed: {str(e)}"}

    def clear_cache(
        self, account_id: Optional[str] = None, backup: bool = True
    ) -> Dict[str, Any]:
        """
        Clear cache for a specific account or all accounts.

        Args:
            account_id: Account ID to clear cache for (if None, clears all accounts)
            backup: Whether to create a backup before clearing

        Returns:
            Dictionary containing cache clearing results
        """
        try:
            if account_id:
                session_dir = self.get_session_dir(account_id)
                logger.info(f"Clearing cache for account {account_id}")
                return self.cache_manager.clear_session_cache(session_dir, backup)
            else:
                sessions_base_dir = self.browser_manager._sessions_base_dir
                logger.info("Clearing cache for all accounts")
                return self.cache_manager.clear_all_sessions_cache(
                    sessions_base_dir, backup
                )
        except Exception as e:
            logger.error(f"Cache clearing failed: {str(e)}")
            return {"success": False, "error": f"Cache clearing failed: {str(e)}"}

    def clear_cache_async(
        self,
        account_id: Optional[str] = None,
        backup: bool = True,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Clear cache asynchronously with progress updates.

        Args:
            account_id: Account ID to clear cache for (if None, clears all accounts)
            backup: Whether to create a backup before clearing
            progress_callback: Callback for progress updates
        """

        def clear_thread():
            """Run cache clearing in a separate thread."""
            try:
                if progress_callback:
                    progress_callback("Starting cache clearing...")

                result = self.clear_cache(account_id, backup)

                if result.get("success"):
                    if account_id:
                        size_cleared = result.get("cleared_size_mb", 0)
                        message = f"Cache cleared for account {account_id}: {size_cleared} MB freed"
                    else:
                        size_cleared = result.get("total_cleared_size_mb", 0)
                        sessions_processed = result.get("sessions_processed", 0)
                        message = f"Cache cleared for {sessions_processed} sessions: {size_cleared} MB freed"

                    logger.info(message)
                    if progress_callback:
                        progress_callback(message)
                else:
                    error_msg = result.get("error", "Unknown error occurred")
                    logger.error(f"Cache clearing failed: {error_msg}")
                    if progress_callback:
                        progress_callback(f"Cache clearing failed: {error_msg}")

            except Exception as e:
                error_msg = f"Cache clearing thread failed: {str(e)}"
                logger.error(error_msg)
                if progress_callback:
                    progress_callback(error_msg)

        # Start cache clearing in a thread to keep UI responsive
        clear_thread = threading.Thread(target=clear_thread)
        clear_thread.daemon = True
        clear_thread.start()

    def restore_session_from_backup(
        self, account_id: str, backup_path: str
    ) -> Dict[str, Any]:
        """
        Restore a session from backup.

        Args:
            account_id: Account ID to restore
            backup_path: Path to the backup directory

        Returns:
            Dictionary containing restore operation results
        """
        try:
            session_dir = self.get_session_dir(account_id)
            logger.info(f"Restoring session for account {account_id} from backup")
            return self.cache_manager.restore_from_backup(backup_path, session_dir)
        except Exception as e:
            logger.error(f"Session restore failed: {str(e)}")
            return {"success": False, "error": f"Session restore failed: {str(e)}"}

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics for all sessions.

        Returns:
            Dictionary containing cache statistics
        """
        try:
            sessions_base_dir = self.browser_manager._sessions_base_dir
            return self.cache_manager.get_cache_statistics(sessions_base_dir)
        except Exception as e:
            logger.error(f"Failed to get cache statistics: {str(e)}")
            return {"error": f"Failed to get cache statistics: {str(e)}"}

    def is_cache_management_available(self) -> bool:
        """
        Check if cache management is available.

        Returns:
            True if cache management is available
        """
        try:
            return hasattr(self, "cache_manager") and self.cache_manager is not None
        except Exception:
            return False
