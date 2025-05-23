"""
Browser cache management module for Playwright browser contexts.
Provides functionality to clear cache data while preserving session information.
"""

import datetime
import shutil
from pathlib import Path
from typing import Dict

from app.utils.logger import logger


class BrowserCacheManager:
    """
    Manages browser cache operations for persistent browser contexts.
    Handles selective cache clearing while preserving authentication data.
    """

    # Cache directories that are safe to clear (won't affect sessions)
    CLEARABLE_CACHE_DIRS = [
        "Cache",
        "Code Cache",
        "GPUCache",
        "ShaderCache",
        "DawnWebGPUCache",
        "DawnGraphiteCache",
        "GrShaderCache",
        "GraphiteDawnCache",
        "blob_storage",  # Temporary blob storage
    ]

    # Files that are safe to clear
    CLEARABLE_CACHE_FILES = [
        "Visited Links",  # Visited links cache
        "Network Action Predictor",  # Network prediction cache
        "Network Action Predictor-journal",
    ]

    # Critical directories to preserve (contain session data)
    PRESERVE_DIRS = [
        "Local Storage",
        "Session Storage",
        "WebStorage",
        "IndexedDB",
        "databases",
    ]

    # Critical files to preserve (contain session data)
    PRESERVE_FILES = [
        "Cookies",
        "Login Data",
        "Login Data For Account",
        "Web Data",
        "Preferences",
        "Secure Preferences",
        "History",
        "Bookmarks",
    ]

    def __init__(self):
        """Initialize the cache manager."""
        self.cleared_size = 0
        self.preserved_size = 0

    def analyze_session_cache(self, session_dir: str) -> Dict[str, any]:
        """
        Analyze cache usage in a browser session directory.

        Args:
            session_dir: Path to the session directory

        Returns:
            Dictionary containing cache analysis results
        """
        session_path = Path(session_dir)
        if not session_path.exists():
            return {"error": f"Session directory not found: {session_dir}"}

        default_path = session_path / "Default"
        if not default_path.exists():
            return {"error": f"Default profile not found in: {session_dir}"}

        analysis = {
            "session_dir": session_dir,
            "total_size": 0,
            "clearable_size": 0,
            "preserved_size": 0,
            "clearable_items": [],
            "preserved_items": [],
            "error": None,
        }

        try:
            # Analyze all items in Default directory
            for item in default_path.iterdir():
                item_size = self._get_size(item)
                analysis["total_size"] += item_size

                item_info = {
                    "name": item.name,
                    "path": str(item),
                    "size": item_size,
                    "size_mb": round(item_size / (1024 * 1024), 2),
                    "type": "directory" if item.is_dir() else "file",
                }

                if self._is_clearable_item(item.name):
                    analysis["clearable_size"] += item_size
                    analysis["clearable_items"].append(item_info)
                else:
                    analysis["preserved_size"] += item_size
                    analysis["preserved_items"].append(item_info)

            analysis["total_size_mb"] = round(analysis["total_size"] / (1024 * 1024), 2)
            analysis["clearable_size_mb"] = round(
                analysis["clearable_size"] / (1024 * 1024), 2
            )
            analysis["preserved_size_mb"] = round(
                analysis["preserved_size"] / (1024 * 1024), 2
            )

        except Exception as e:
            analysis["error"] = f"Error analyzing session cache: {str(e)}"
            logger.error(f"Cache analysis failed for {session_dir}: {str(e)}")

        return analysis

    def clear_session_cache(
        self, session_dir: str, backup: bool = True
    ) -> Dict[str, any]:
        """
        Clear cache from a browser session while preserving session data.

        Args:
            session_dir: Path to the session directory
            backup: Whether to create a backup before clearing

        Returns:
            Dictionary containing operation results
        """
        session_path = Path(session_dir)
        if not session_path.exists():
            return {
                "success": False,
                "error": f"Session directory not found: {session_dir}",
            }

        default_path = session_path / "Default"
        if not default_path.exists():
            return {
                "success": False,
                "error": f"Default profile not found in: {session_dir}",
            }

        result = {
            "success": False,
            "session_dir": session_dir,
            "cleared_items": [],
            "cleared_size": 0,
            "errors": [],
            "backup_path": None,
        }

        try:
            # Create backup if requested
            if backup:
                backup_path = self._create_backup(session_dir)
                result["backup_path"] = backup_path
                logger.info(f"Created backup at: {backup_path}")

            # Clear cache items
            for item in default_path.iterdir():
                if self._is_clearable_item(item.name):
                    try:
                        item_size = self._get_size(item)

                        # Check if item is locked before attempting deletion
                        if self._is_item_locked(item):
                            error_msg = (
                                f"Cannot clear {item.name}: file is locked or in use"
                            )
                            result["errors"].append(error_msg)
                            logger.warning(error_msg)
                            continue

                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()

                        result["cleared_items"].append(
                            {
                                "name": item.name,
                                "size": item_size,
                                "size_mb": round(item_size / (1024 * 1024), 2),
                            }
                        )
                        result["cleared_size"] += item_size

                        logger.info(
                            f"Cleared cache item: {item.name} ({round(item_size / (1024 * 1024), 2)} MB)"
                        )

                    except Exception as e:
                        error_msg = f"Failed to clear {item.name}: {str(e)}"
                        result["errors"].append(error_msg)
                        logger.error(error_msg)

            result["cleared_size_mb"] = round(result["cleared_size"] / (1024 * 1024), 2)

            # Improved success criteria: successful if no errors, even if nothing to clear
            result["success"] = len(result["errors"]) == 0

            if result["success"]:
                if len(result["cleared_items"]) > 0:
                    logger.info(
                        f"Cache clearing completed. Cleared {result['cleared_size_mb']} MB from {len(result['cleared_items'])} items"
                    )
                else:
                    logger.info(
                        "Cache clearing completed. No cache items found to clear"
                    )
            else:
                logger.warning(
                    f"Cache clearing completed with {len(result['errors'])} errors"
                )

        except Exception as e:
            result["error"] = f"Cache clearing failed: {str(e)}"
            logger.error(f"Cache clearing failed for {session_dir}: {str(e)}")

        return result

    def clear_all_sessions_cache(
        self, sessions_base_dir: str, backup: bool = True
    ) -> Dict[str, any]:
        """
        Clear cache from all browser sessions.

        Args:
            sessions_base_dir: Path to the sessions base directory
            backup: Whether to create backups before clearing

        Returns:
            Dictionary containing operation results for all sessions
        """
        sessions_path = Path(sessions_base_dir)
        if not sessions_path.exists():
            return {
                "success": False,
                "error": f"Sessions directory not found: {sessions_base_dir}",
            }

        result = {
            "success": False,
            "sessions_processed": 0,
            "total_cleared_size": 0,
            "session_results": {},
            "errors": [],
        }

        try:
            session_dirs = [
                d
                for d in sessions_path.iterdir()
                if d.is_dir() and d.name.startswith("session_")
            ]

            for session_dir in session_dirs:
                session_result = self.clear_session_cache(str(session_dir), backup)
                result["session_results"][session_dir.name] = session_result

                if session_result.get("success"):
                    result["sessions_processed"] += 1
                    result["total_cleared_size"] += session_result.get(
                        "cleared_size", 0
                    )

                if session_result.get("errors"):
                    result["errors"].extend(session_result["errors"])

            result["total_cleared_size_mb"] = round(
                result["total_cleared_size"] / (1024 * 1024), 2
            )
            result["success"] = result["sessions_processed"] > 0

            logger.info(
                f"Bulk cache clearing completed. Processed {result['sessions_processed']} sessions, cleared {result['total_cleared_size_mb']} MB total"
            )

        except Exception as e:
            result["error"] = f"Bulk cache clearing failed: {str(e)}"
            logger.error(f"Bulk cache clearing failed: {str(e)}")

        return result

    def restore_from_backup(self, backup_path: str, session_dir: str) -> Dict[str, any]:
        """
        Restore session from backup.

        Args:
            backup_path: Path to the backup directory
            session_dir: Path to the session directory to restore to

        Returns:
            Dictionary containing restore operation results
        """
        backup_path_obj = Path(backup_path)
        session_path_obj = Path(session_dir)

        if not backup_path_obj.exists():
            return {"success": False, "error": f"Backup not found: {backup_path}"}

        try:
            # Remove current session if it exists
            if session_path_obj.exists():
                shutil.rmtree(session_path_obj)

            # Restore from backup
            shutil.copytree(backup_path, session_dir)

            logger.info(f"Successfully restored session from backup: {backup_path}")
            return {"success": True, "message": "Session restored successfully"}

        except Exception as e:
            error_msg = f"Failed to restore from backup: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _is_clearable_item(self, item_name: str) -> bool:
        """
        Check if an item is safe to clear (won't affect session data).

        Args:
            item_name: Name of the file or directory

        Returns:
            True if the item can be safely cleared
        """
        # Check against clearable lists (explicit allow-list)
        if (
            item_name in self.CLEARABLE_CACHE_DIRS
            or item_name in self.CLEARABLE_CACHE_FILES
        ):
            return True

        # Check against preserve lists (explicit deny-list) - takes precedence
        if item_name in self.PRESERVE_DIRS or item_name in self.PRESERVE_FILES:
            return False

        # More conservative heuristics for cache-like items
        # Only clear if the name starts or ends with cache indicators
        cache_indicators = [
            "cache",
            "Cache",
            "CACHE",
            "temp",
            "Temp",
            "TEMP",
            "tmp",
            "TMP",
        ]

        # Check for exact matches or safe patterns
        for indicator in cache_indicators:
            # Only clear if it starts with the indicator or ends with it
            if (
                item_name.startswith(indicator)
                or item_name.endswith(indicator)
                or item_name.endswith(f".{indicator.lower()}")
                or item_name.endswith(f"_{indicator.lower()}")
            ):
                # Extra safety: don't clear anything with "data", "storage", "login", "session"
                safety_keywords = [
                    "data",
                    "storage",
                    "login",
                    "session",
                    "user",
                    "profile",
                ]
                if any(
                    keyword.lower() in item_name.lower() for keyword in safety_keywords
                ):
                    return False
                return True

        # Default to preserve unknown items to be safe
        return False

    def _get_size(self, path: Path) -> int:
        """
        Get the total size of a file or directory.

        Args:
            path: Path to measure

        Returns:
            Size in bytes
        """
        if path.is_file():
            try:
                return path.stat().st_size
            except (OSError, PermissionError) as e:
                logger.warning(f"Cannot access file {path}: {e}")
                return 0
        elif path.is_dir():
            total = 0
            inaccessible_items = 0
            try:
                for item in path.rglob("*"):
                    if item.is_file():
                        try:
                            total += item.stat().st_size
                        except (OSError, PermissionError):
                            inaccessible_items += 1
            except (OSError, PermissionError) as e:
                logger.warning(f"Cannot fully access directory {path}: {e}")

            if inaccessible_items > 0:
                logger.info(
                    f"Could not access {inaccessible_items} items in {path}, size may be underreported"
                )
            return total
        return 0

    def _create_backup(self, session_dir: str) -> str:
        """
        Create a backup of the session directory.

        Args:
            session_dir: Path to the session directory

        Returns:
            Path to the backup directory
        """
        session_path = Path(session_dir)
        backup_dir = session_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Use microseconds to prevent timestamp collisions
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_name = f"{session_path.name}_backup_{timestamp}"
        backup_path = backup_dir / backup_name

        # Handle potential conflicts with a counter
        counter = 1
        original_backup_path = backup_path
        while backup_path.exists():
            backup_path = backup_dir / f"{original_backup_path.name}_{counter}"
            counter += 1

        shutil.copytree(session_dir, backup_path)
        return str(backup_path)

    def get_cache_statistics(self, sessions_base_dir: str) -> Dict[str, any]:
        """
        Get cache statistics for all sessions.

        Args:
            sessions_base_dir: Path to the sessions base directory

        Returns:
            Dictionary containing cache statistics
        """
        sessions_path = Path(sessions_base_dir)
        if not sessions_path.exists():
            return {"error": f"Sessions directory not found: {sessions_base_dir}"}

        stats = {
            "total_sessions": 0,
            "total_size": 0,
            "total_clearable_size": 0,
            "total_preserved_size": 0,
            "sessions": [],
        }

        try:
            session_dirs = [
                d
                for d in sessions_path.iterdir()
                if d.is_dir() and d.name.startswith("session_")
            ]

            for session_dir in session_dirs:
                analysis = self.analyze_session_cache(str(session_dir))
                if not analysis.get("error"):
                    stats["total_sessions"] += 1
                    stats["total_size"] += analysis.get("total_size", 0)
                    stats["total_clearable_size"] += analysis.get("clearable_size", 0)
                    stats["total_preserved_size"] += analysis.get("preserved_size", 0)

                    stats["sessions"].append(
                        {
                            "name": session_dir.name,
                            "total_size_mb": analysis.get("total_size_mb", 0),
                            "clearable_size_mb": analysis.get("clearable_size_mb", 0),
                            "preserved_size_mb": analysis.get("preserved_size_mb", 0),
                        }
                    )

            stats["total_size_mb"] = round(stats["total_size"] / (1024 * 1024), 2)
            stats["total_clearable_size_mb"] = round(
                stats["total_clearable_size"] / (1024 * 1024), 2
            )
            stats["total_preserved_size_mb"] = round(
                stats["total_preserved_size"] / (1024 * 1024), 2
            )

        except Exception as e:
            stats["error"] = f"Failed to get cache statistics: {str(e)}"
            logger.error(f"Cache statistics failed: {str(e)}")

        return stats

    def _is_item_locked(self, path: Path) -> bool:
        """
        Check if a file or directory is locked or in use.

        Args:
            path: Path to the file or directory

        Returns:
            True if the item is locked or in use
        """
        try:
            if not path.exists():
                return False

            if path.is_file():
                # Try to open the file in write mode to check for locks
                with open(path, "r+b") as f:
                    pass
            elif path.is_dir():
                # Try to rename the directory temporarily to check for locks
                temp_name = f"{path.name}_temp_check"
                temp_path = path.parent / temp_name
                path.rename(temp_path)
                temp_path.rename(path)  # Rename back immediately

            return False
        except (OSError, PermissionError):
            return True
