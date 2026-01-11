"""
Process guard for managing orphaned processes.

When the desktop app crashes, it may leave Ollama running.
This module provides utilities to detect and clean up orphaned processes.
"""
import os
import sys
import signal
import logging
from pathlib import Path
from typing import Optional

from backend.config import get_settings

logger = logging.getLogger("techtime.desktop.process_guard")


class ProcessGuard:
    """
    Manages a PID file to track the Ollama process we started.
    
    On startup, checks for orphaned processes from previous runs
    and cleans them up.
    """
    
    def __init__(self, name: str = "ollama"):
        """
        Initialize the process guard.
        
        Args:
            name: Process name for the PID file
        """
        self.name = name
        settings = get_settings()
        self._pid_file = settings.user_data_path / f".{name}.pid"
    
    def check_and_cleanup(self) -> bool:
        """
        Check for orphaned process and clean up if found.
        
        Returns:
            True if an orphan was found and cleaned up
        """
        if not self._pid_file.exists():
            return False
        
        try:
            pid = int(self._pid_file.read_text().strip())
            
            # Check if process is still running
            if self._is_process_running(pid):
                logger.warning(f"Found orphaned {self.name} process (PID {pid})")
                
                # Try to terminate it
                if self._terminate_process(pid):
                    logger.info(f"Terminated orphaned {self.name} process")
                    self._cleanup_pid_file()
                    return True
                else:
                    logger.error(f"Failed to terminate orphaned process {pid}")
            else:
                # Process is gone, just clean up PID file
                logger.debug(f"Stale PID file found, cleaning up")
                self._cleanup_pid_file()
                
        except ValueError:
            # Invalid PID in file
            logger.warning("Invalid PID file, cleaning up")
            self._cleanup_pid_file()
        except Exception as e:
            logger.error(f"Error checking for orphaned process: {e}")
        
        return False
    
    def register_pid(self, pid: int) -> None:
        """
        Register a PID for tracking.
        
        Args:
            pid: Process ID to track
        """
        try:
            self._pid_file.parent.mkdir(parents=True, exist_ok=True)
            self._pid_file.write_text(str(pid))
            logger.debug(f"Registered {self.name} PID: {pid}")
        except Exception as e:
            logger.warning(f"Failed to register PID: {e}")
    
    def unregister(self) -> None:
        """Remove the PID file (called on clean shutdown)."""
        self._cleanup_pid_file()
    
    def _cleanup_pid_file(self) -> None:
        """Remove the PID file."""
        try:
            if self._pid_file.exists():
                self._pid_file.unlink()
        except Exception as e:
            logger.warning(f"Failed to remove PID file: {e}")
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is running."""
        if sys.platform == 'win32':
            return self._is_running_windows(pid)
        else:
            return self._is_running_unix(pid)
    
    def _is_running_unix(self, pid: int) -> bool:
        """Check if process is running on Unix."""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    
    def _is_running_windows(self, pid: int) -> bool:
        """Check if process is running on Windows."""
        import ctypes
        
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        
        try:
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION,
                False,
                pid
            )
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False
    
    def _terminate_process(self, pid: int) -> bool:
        """Terminate a process by PID."""
        try:
            if sys.platform == 'win32':
                # Windows
                import ctypes
                PROCESS_TERMINATE = 0x0001
                handle = ctypes.windll.kernel32.OpenProcess(
                    PROCESS_TERMINATE,
                    False,
                    pid
                )
                if handle:
                    result = ctypes.windll.kernel32.TerminateProcess(handle, 1)
                    ctypes.windll.kernel32.CloseHandle(handle)
                    return bool(result)
            else:
                # Unix
                os.kill(pid, signal.SIGTERM)
                
                # Wait briefly for graceful shutdown
                import time
                for _ in range(10):
                    time.sleep(0.5)
                    if not self._is_running_unix(pid):
                        return True
                
                # Force kill if still running
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to terminate process {pid}: {e}")
            return False


# Convenience function
def cleanup_orphaned_ollama() -> bool:
    """
    Clean up any orphaned Ollama processes from previous crashes.
    
    Call this early in application startup.
    
    Returns:
        True if an orphan was found and cleaned up
    """
    guard = ProcessGuard("ollama")
    return guard.check_and_cleanup()
