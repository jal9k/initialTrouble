"""Script runner for native shell diagnostic scripts.

This module provides a thin Python layer that executes platform-specific
shell scripts and parses their JSON output into DiagnosticResult objects.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from .base import DiagnosticResult
from .platform import Platform, get_platform


# Script directories by platform
SCRIPT_DIRS = {
    Platform.MACOS: Path(__file__).parent / "macos",
    Platform.LINUX: Path(__file__).parent / "linux",
    Platform.WINDOWS: Path(__file__).parent / "windows_scripts",
}

# Script extensions by platform
SCRIPT_EXTENSIONS = {
    Platform.MACOS: ".sh",
    Platform.LINUX: ".sh",
    Platform.WINDOWS: ".ps1",
}


class ScriptRunner:
    """Execute diagnostic scripts and parse their JSON output."""

    def __init__(self, timeout: int = 30):
        """Initialize the script runner.
        
        Args:
            timeout: Default timeout for script execution in seconds
        """
        self.timeout = timeout
        self.platform = get_platform()
        self.script_dir = SCRIPT_DIRS.get(self.platform)
        self.extension = SCRIPT_EXTENSIONS.get(self.platform, ".sh")

    def get_script_path(self, script_name: str) -> Path | None:
        """Get the full path to a script.
        
        Args:
            script_name: Name of the script (without extension)
            
        Returns:
            Path to the script, or None if not found
        """
        if self.script_dir is None:
            return None
        
        script_path = self.script_dir / f"{script_name}{self.extension}"
        if script_path.exists():
            return script_path
        return None

    async def run_script(
        self,
        script_name: str,
        args: list[str] | None = None,
        timeout: int | None = None,
    ) -> DiagnosticResult:
        """Execute a diagnostic script and return the result.
        
        Args:
            script_name: Name of the script (without extension)
            args: Command-line arguments to pass to the script
            timeout: Override default timeout
            
        Returns:
            DiagnosticResult parsed from script JSON output
        """
        script_path = self.get_script_path(script_name)
        
        if script_path is None:
            return DiagnosticResult(
                success=False,
                function_name=script_name,
                platform=self.platform.value,
                error=f"Script not found: {script_name}{self.extension}",
                suggestions=[
                    f"Script not available for platform: {self.platform.value}",
                    "Check that the script exists in the correct directory",
                ],
            )

        # Build command based on platform
        args = args or []
        
        if self.platform == Platform.WINDOWS:
            # Use PowerShell to execute .ps1 scripts
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-File", str(script_path),
                *args,
            ]
        else:
            # Use bash for .sh scripts
            cmd = ["bash", str(script_path), *args]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout or self.timeout,
            )

            # Decode output
            encoding = "utf-8" if self.platform != Platform.WINDOWS else "cp1252"
            stdout_str = stdout.decode(encoding, errors="replace").strip()
            stderr_str = stderr.decode(encoding, errors="replace").strip()

            # Parse JSON output
            return self._parse_output(
                script_name=script_name,
                stdout=stdout_str,
                stderr=stderr_str,
                return_code=process.returncode or 0,
            )

        except asyncio.TimeoutError:
            return DiagnosticResult(
                success=False,
                function_name=script_name,
                platform=self.platform.value,
                error=f"Script timed out after {timeout or self.timeout} seconds",
                suggestions=["Try running the script manually to debug"],
            )

        except Exception as e:
            return DiagnosticResult(
                success=False,
                function_name=script_name,
                platform=self.platform.value,
                error=f"Failed to execute script: {str(e)}",
                suggestions=["Check script permissions and syntax"],
            )

    def _parse_output(
        self,
        script_name: str,
        stdout: str,
        stderr: str,
        return_code: int,
    ) -> DiagnosticResult:
        """Parse script output into a DiagnosticResult.
        
        Args:
            script_name: Name of the script
            stdout: Standard output from script
            stderr: Standard error from script
            return_code: Process return code
            
        Returns:
            Parsed DiagnosticResult
        """
        # Try to parse JSON from stdout
        try:
            data = json.loads(stdout)
            
            return DiagnosticResult(
                success=data.get("success", return_code == 0),
                function_name=script_name,
                platform=self.platform.value,
                data=data.get("data", {}),
                raw_output=stdout,
                error=data.get("error"),
                suggestions=data.get("suggestions", []),
            )

        except json.JSONDecodeError:
            # If JSON parsing fails, treat as error
            error_msg = stderr if stderr else f"Invalid JSON output: {stdout[:200]}"
            
            return DiagnosticResult(
                success=False,
                function_name=script_name,
                platform=self.platform.value,
                raw_output=stdout,
                error=error_msg,
                suggestions=[
                    "Script did not return valid JSON",
                    "Check script output format",
                ],
            )


# Global runner instance
_runner: ScriptRunner | None = None


def get_runner(timeout: int = 30) -> ScriptRunner:
    """Get or create global script runner."""
    global _runner
    if _runner is None:
        _runner = ScriptRunner(timeout=timeout)
    return _runner


async def run_diagnostic_script(
    script_name: str,
    args: list[str] | None = None,
    timeout: int | None = None,
) -> DiagnosticResult:
    """Convenience function to run a diagnostic script.
    
    Args:
        script_name: Name of the script (without extension)
        args: Command-line arguments to pass to the script
        timeout: Override default timeout
        
    Returns:
        DiagnosticResult from script execution
    """
    runner = get_runner()
    return await runner.run_script(script_name, args, timeout)


def script_exists(script_name: str) -> bool:
    """Check if a script exists for the current platform.
    
    Args:
        script_name: Name of the script (without extension)
        
    Returns:
        True if script exists, False otherwise
    """
    runner = get_runner()
    return runner.get_script_path(script_name) is not None
