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
            # First, calculate the true total size of the entire session directory
            session_total_size = self._get_size(session_path)

            # Initialize counters for Default directory analysis
            default_clearable_size = 0
            default_preserved_size = 0

            # Analyze items in Default directory
            for item in default_path.iterdir():
                item_size = self._get_size(item)

                item_info = {
                    "name": item.name,
                    "path": str(item),
                    "size": item_size,
                    "size_mb": round(item_size / (1024 * 1024), 2),
                    "type": "directory" if item.is_dir() else "file",
                }

                if self._is_clearable_item(item.name):
                    default_clearable_size += item_size
                    analysis["clearable_items"].append(item_info)
                else:
                    default_preserved_size += item_size
                    analysis["preserved_items"].append(item_info)

            # Calculate sizes for directories outside Default (typically cache-related)
            external_size = session_total_size - self._get_size(default_path)

            # Most external directories are cache-related and clearable
            # but we need to be conservative about what we consider clearable
            external_clearable_size = 0
            external_preserved_size = 0

            for item in session_path.iterdir():
                if item.name == "Default":
                    continue

                item_size = self._get_size(item)

                # External cache directories that are safe to clear
                external_cache_dirs = [
                    "ShaderCache",
                    "GrShaderCache",
                    "GraphiteDawnCache",
                    "component_crx_cache",
                    "TrustTokenKeyCommitments",
                    "ThirdPartyModuleList64",
                    "Subresource Filter",
                    "SSLErrorAssistant",
                    "segmentation_platform",
                    "SafetyTips",
                    "PrivacySandboxAttestationsPreloaded",
                    "PKIMetadata",
                    "OriginTrials",
                    "optimization_guide_model_store",
                    "MediaFoundationWidevineCdm",
                    "Crowd Deny",
                    "Crashpad",
                    "CertificateRevocation",
                    "FirstPartySetsPreloaded",
                    "screen_ai",
                    "ProbabilisticRevealTokenRegistry",
                    "AmountExtractionHeuristicRegexes",
                    "AutofillStates",
                    "CookieReadinessList",
                    "OpenCookieDatabase",
                    "TpcdMetadata",
                    "ZxcvbnData",
                    "hyphen-data",
                    "MEIPreload",
                    "FileTypePolicies",
                    "OnDeviceHeadSuggestModel",
                    "OptimizationHints",
                    "WidevineCdm",
                    "RecoveryImproved",
                    "Safe Browsing",
                ]

                if item.name in external_cache_dirs or self._is_clearable_item(
                    item.name
                ):
                    external_clearable_size += item_size
                    analysis["clearable_items"].append(
                        {
                            "name": item.name,
                            "path": str(item),
                            "size": item_size,
                            "size_mb": round(item_size / (1024 * 1024), 2),
                            "type": "directory" if item.is_dir() else "file",
                        }
                    )
                else:
                    external_preserved_size += item_size
                    analysis["preserved_items"].append(
                        {
                            "name": item.name,
                            "path": str(item),
                            "size": item_size,
                            "size_mb": round(item_size / (1024 * 1024), 2),
                            "type": "directory" if item.is_dir() else "file",
                        }
                    )

            # Set final calculations
            analysis["total_size"] = session_total_size
            analysis["clearable_size"] = (
                default_clearable_size + external_clearable_size
            )
            analysis["preserved_size"] = (
                default_preserved_size + external_preserved_size
            )

            # Convert to MB
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
        Get the total size of a file or directory with improved accuracy and error handling.

        Args:
            path: Path to measure

        Returns:
            Size in bytes
        """
        if not path.exists():
            return 0

        if path.is_file():
            try:
                return path.stat().st_size
            except (OSError, PermissionError) as e:
                logger.debug(f"Cannot access file {path}: {e}")
                return 0
        elif path.is_dir():
            total = 0
            accessible_files = 0
            inaccessible_files = 0

            try:
                # Use a more efficient approach for directory traversal
                for item in path.rglob("*"):
                    if item.is_file():
                        try:
                            size = item.stat().st_size
                            total += size
                            accessible_files += 1
                        except (OSError, PermissionError, FileNotFoundError):
                            inaccessible_files += 1

                # Log detailed information only if there are inaccessible files
                if inaccessible_files > 0:
                    logger.debug(
                        f"Directory {path}: {accessible_files} files accessible "
                        f"({total / (1024 * 1024):.2f} MB), "
                        f"{inaccessible_files} files inaccessible"
                    )
                else:
                    logger.debug(
                        f"Directory {path}: {accessible_files} files "
                        f"({total / (1024 * 1024):.2f} MB)"
                    )

            except (OSError, PermissionError) as e:
                # If we can't access the directory at all, try to get just the directory size
                try:
                    logger.debug(f"Cannot fully traverse directory {path}: {e}")
                    return path.stat().st_size
                except (OSError, PermissionError):
                    logger.debug(f"Cannot access directory {path} at all: {e}")
                    return 0

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

    def get_comprehensive_storage_stats(self, sessions_base_dir: str) -> Dict[str, any]:
        """
        Get comprehensive storage statistics including all session directories and subdirectories.
        This provides more accurate storage usage than the cache-focused analysis.

        Args:
            sessions_base_dir: Path to the sessions base directory

        Returns:
            Dictionary containing comprehensive storage statistics
        """
        sessions_path = Path(sessions_base_dir)
        if not sessions_path.exists():
            return {"error": f"Sessions directory not found: {sessions_base_dir}"}

        stats = {
            "total_sessions": 0,
            "total_storage_size": 0,
            "total_clearable_size": 0,
            "total_preserved_size": 0,
            "total_other_size": 0,  # Files/dirs not categorized as cache or preserved
            "sessions": [],
            "storage_breakdown": {
                "cache_directories": 0,
                "preserved_directories": 0,
                "external_cache": 0,
                "other_data": 0,
            },
        }

        try:
            session_dirs = [
                d
                for d in sessions_path.iterdir()
                if d.is_dir() and d.name.startswith("session_")
            ]

            for session_dir in session_dirs:
                # Get both cache analysis and comprehensive storage info
                cache_analysis = self.analyze_session_cache(str(session_dir))

                if not cache_analysis.get("error"):
                    stats["total_sessions"] += 1

                    # Use total_size from comprehensive analysis
                    session_total = cache_analysis.get("total_size", 0)
                    session_clearable = cache_analysis.get("clearable_size", 0)
                    session_preserved = cache_analysis.get("preserved_size", 0)
                    session_other = max(
                        0, session_total - session_clearable - session_preserved
                    )

                    stats["total_storage_size"] += session_total
                    stats["total_clearable_size"] += session_clearable
                    stats["total_preserved_size"] += session_preserved
                    stats["total_other_size"] += session_other

                    # Detailed session info
                    session_info = {
                        "name": session_dir.name,
                        "total_size_mb": round(session_total / (1024 * 1024), 2),
                        "clearable_size_mb": round(
                            session_clearable / (1024 * 1024), 2
                        ),
                        "preserved_size_mb": round(
                            session_preserved / (1024 * 1024), 2
                        ),
                        "other_size_mb": round(session_other / (1024 * 1024), 2),
                        "clearable_items_count": len(
                            cache_analysis.get("clearable_items", [])
                        ),
                        "preserved_items_count": len(
                            cache_analysis.get("preserved_items", [])
                        ),
                    }
                    stats["sessions"].append(session_info)

            # Convert totals to MB
            stats["total_storage_size_mb"] = round(
                stats["total_storage_size"] / (1024 * 1024), 2
            )
            stats["total_clearable_size_mb"] = round(
                stats["total_clearable_size"] / (1024 * 1024), 2
            )
            stats["total_preserved_size_mb"] = round(
                stats["total_preserved_size"] / (1024 * 1024), 2
            )
            stats["total_other_size_mb"] = round(
                stats["total_other_size"] / (1024 * 1024), 2
            )

            # Calculate percentages
            if stats["total_storage_size"] > 0:
                stats["clearable_percentage"] = round(
                    (stats["total_clearable_size"] / stats["total_storage_size"]) * 100,
                    1,
                )
                stats["preserved_percentage"] = round(
                    (stats["total_preserved_size"] / stats["total_storage_size"]) * 100,
                    1,
                )
                stats["other_percentage"] = round(
                    (stats["total_other_size"] / stats["total_storage_size"]) * 100, 1
                )
            else:
                stats["clearable_percentage"] = 0
                stats["preserved_percentage"] = 0
                stats["other_percentage"] = 0

        except Exception as e:
            stats["error"] = f"Failed to get comprehensive storage statistics: {str(e)}"
            logger.error(f"Comprehensive storage analysis failed: {str(e)}")

        return stats

    def get_cache_statistics(self, sessions_base_dir: str) -> Dict[str, any]:
        """
        Get cache statistics for all sessions.
        Enhanced to provide comprehensive storage information.

        Args:
            sessions_base_dir: Path to the sessions base directory

        Returns:
            Dictionary containing cache statistics
        """
        # Use the comprehensive analysis for more accurate results
        comprehensive_stats = self.get_comprehensive_storage_stats(sessions_base_dir)

        if comprehensive_stats.get("error"):
            return comprehensive_stats

        # Return in the expected cache statistics format for backward compatibility
        # but with enhanced accuracy from comprehensive analysis
        return {
            "total_sessions": comprehensive_stats["total_sessions"],
            "total_size": comprehensive_stats["total_storage_size"],
            "total_clearable_size": comprehensive_stats["total_clearable_size"],
            "total_preserved_size": comprehensive_stats["total_preserved_size"],
            "total_other_size": comprehensive_stats["total_other_size"],
            "total_size_mb": comprehensive_stats["total_storage_size_mb"],
            "total_clearable_size_mb": comprehensive_stats["total_clearable_size_mb"],
            "total_preserved_size_mb": comprehensive_stats["total_preserved_size_mb"],
            "total_other_size_mb": comprehensive_stats["total_other_size_mb"],
            "sessions": comprehensive_stats["sessions"],
            "clearable_percentage": comprehensive_stats.get("clearable_percentage", 0),
            "preserved_percentage": comprehensive_stats.get("preserved_percentage", 0),
            "other_percentage": comprehensive_stats.get("other_percentage", 0),
            "storage_breakdown": comprehensive_stats.get("storage_breakdown", {}),
            "analysis_type": "comprehensive",  # Indicator that this uses enhanced analysis
        }

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
