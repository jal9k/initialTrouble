"""Temporary file cleanup diagnostic.

Removes temporary files from standard cache and temp locations
to free disk space and potentially resolve application issues.

See documents/functions/cleanup_temp_files.md for full specification.
"""

import os
import time
from glob import glob
from pathlib import Path
from typing import Any

from .base import BaseDiagnostic, DiagnosticResult
from .platform import Platform


class CleanupTempFiles(BaseDiagnostic):
    """Clean up temporary files to free disk space."""

    name = "cleanup_temp_files"
    description = "Remove temporary files to free disk space"
    osi_layer = "Application"

    # Files modified within this many seconds are skipped for safety
    MIN_AGE_SECONDS = 3600  # 1 hour

    # Platform-specific paths for cleanup
    PATHS = {
        Platform.MACOS: {
            "standard": [
                "~/Library/Caches",
                "/tmp",
                "/var/folders/*/*/T",
            ],
            "aggressive": [
                "~/Library/Logs",
                "~/.Trash",
            ],
        },
        Platform.WINDOWS: {
            "standard": [
                "%TEMP%",
                "%LOCALAPPDATA%\\Temp",
                "C:\\Windows\\Temp",
            ],
            "aggressive": [
                "%LOCALAPPDATA%\\Microsoft\\Windows\\INetCache",
            ],
        },
        Platform.LINUX: {
            "standard": [
                "/tmp",
                "/var/tmp",
                "~/.cache",
            ],
            "aggressive": [
                "~/.local/share/Trash",
            ],
        },
    }

    # Directories to never delete (safety list)
    PROTECTED_DIRS = {
        # System critical
        "/", "/bin", "/sbin", "/usr", "/etc", "/var", "/lib", "/lib64",
        "/System", "/Library", "/Applications",
        "C:\\Windows", "C:\\Windows\\System32", "C:\\Program Files",
        # User critical
        "~/Desktop", "~/Documents", "~/Downloads",
    }

    async def run(
        self,
        aggressive: bool = False,
        dry_run: bool = False,
    ) -> DiagnosticResult:
        """
        Clean up temporary files.

        Args:
            aggressive: Include additional cache locations (default: False)
            dry_run: Report what would be deleted without deleting (default: False)

        Returns:
            DiagnosticResult with cleanup statistics
        """
        paths = self._get_paths(aggressive)

        files_deleted = 0
        space_freed = 0
        errors: list[str] = []
        skipped: list[str] = []

        for path_pattern in paths:
            expanded_paths = self._expand_path(path_pattern)

            for path in expanded_paths:
                if not path.exists():
                    continue

                if not path.is_dir():
                    continue

                # Safety check - don't clean protected directories
                if self._is_protected(path):
                    skipped.append(f"Protected: {path}")
                    continue

                result = await self._clean_directory(
                    path, dry_run, errors, skipped
                )
                files_deleted += result["files"]
                space_freed += result["bytes"]

        return self._success(
            data={
                "files_deleted": files_deleted,
                "space_freed_mb": round(space_freed / (1024 * 1024), 2),
                "space_freed_bytes": space_freed,
                "errors_count": len(errors),
                "errors": errors[:10],  # Limit error list for readability
                "skipped_count": len(skipped),
                "dry_run": dry_run,
                "mode": "aggressive" if aggressive else "standard",
                "paths_scanned": len(paths),
            },
            suggestions=self._generate_suggestions(space_freed, errors, dry_run),
        )

    def _get_paths(self, aggressive: bool) -> list[str]:
        """Get list of paths to clean for current platform."""
        platform_paths = self.PATHS.get(self.platform, self.PATHS[Platform.LINUX])
        paths = platform_paths["standard"].copy()
        if aggressive:
            paths.extend(platform_paths["aggressive"])
        return paths

    def _expand_path(self, path_pattern: str) -> list[Path]:
        """Expand environment variables and globs in path."""
        # Expand ~ and environment variables
        expanded = os.path.expanduser(os.path.expandvars(path_pattern))

        # Handle glob patterns
        if "*" in expanded:
            return [Path(p) for p in glob(expanded)]

        return [Path(expanded)]

    def _is_protected(self, path: Path) -> bool:
        """Check if a path is in the protected list."""
        path_str = str(path.resolve())
        for protected in self.PROTECTED_DIRS:
            protected_expanded = os.path.expanduser(protected)
            if path_str == protected_expanded or path_str.startswith(protected_expanded + os.sep):
                # Only protect if it's the exact path, not subdirectories we want to clean
                if path_str == protected_expanded:
                    return True
        return False

    async def _clean_directory(
        self,
        directory: Path,
        dry_run: bool,
        errors: list[str],
        skipped: list[str],
    ) -> dict[str, int]:
        """Clean a single directory, returning stats."""
        files_deleted = 0
        bytes_freed = 0

        try:
            for item in directory.rglob("*"):
                if item.is_file():
                    try:
                        # Skip recently modified files for safety
                        mtime = item.stat().st_mtime
                        if time.time() - mtime < self.MIN_AGE_SECONDS:
                            skipped.append(f"Recent: {item}")
                            continue

                        # Get file size before deletion
                        size = item.stat().st_size

                        if not dry_run:
                            item.unlink()

                        files_deleted += 1
                        bytes_freed += size

                    except PermissionError:
                        errors.append(f"Permission denied: {item}")
                    except FileNotFoundError:
                        # File was deleted by another process
                        pass
                    except Exception as e:
                        errors.append(f"{item}: {e}")

        except PermissionError:
            errors.append(f"Cannot access directory: {directory}")
        except Exception as e:
            errors.append(f"Error scanning {directory}: {e}")

        return {"files": files_deleted, "bytes": bytes_freed}

    def _generate_suggestions(
        self,
        space_freed: int,
        errors: list[str],
        dry_run: bool,
    ) -> list[str]:
        """Generate suggestions based on results."""
        suggestions = []

        if dry_run:
            suggestions.append(
                "This was a dry run. Run with dry_run=False to actually delete files."
            )

        if space_freed > 500 * 1024 * 1024:  # > 500MB
            suggestions.append(
                "Significant space recovered. Consider running cleanup regularly."
            )
        elif space_freed > 100 * 1024 * 1024:  # > 100MB
            suggestions.append(
                f"Recovered {round(space_freed / (1024 * 1024), 1)}MB of disk space."
            )
        elif space_freed < 10 * 1024 * 1024:  # < 10MB
            suggestions.append(
                "Minimal temp files found. Your system is already fairly clean."
            )

        if errors:
            suggestions.append(
                f"Some files could not be deleted ({len(errors)} errors). "
                "Run as administrator/root for full cleanup."
            )

        return suggestions if suggestions else None


# Module-level function for easy importing
async def cleanup_temp_files(
    aggressive: bool = False,
    dry_run: bool = False,
) -> DiagnosticResult:
    """Clean up temporary files.
    
    Args:
        aggressive: Include additional cache locations
        dry_run: Report what would be deleted without deleting
        
    Returns:
        DiagnosticResult with cleanup statistics
    """
    diag = CleanupTempFiles()
    return await diag.run(aggressive=aggressive, dry_run=dry_run)

