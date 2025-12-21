"""Platform detection and cross-platform command execution."""

import asyncio
import platform
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Literal


class Platform(Enum):
    """Supported operating systems."""

    MACOS = "macos"
    WINDOWS = "windows"
    LINUX = "linux"
    UNKNOWN = "unknown"

    @classmethod
    def detect(cls) -> "Platform":
        """Detect the current operating system."""
        system = platform.system().lower()
        if system == "darwin":
            return cls.MACOS
        elif system == "windows":
            return cls.WINDOWS
        elif system == "linux":
            return cls.LINUX
        return cls.UNKNOWN

    @property
    def is_unix(self) -> bool:
        """Check if platform is Unix-like."""
        return self in (Platform.MACOS, Platform.LINUX)


@dataclass
class CommandResult:
    """Result of executing a system command."""

    stdout: str
    stderr: str
    return_code: int
    timed_out: bool = False

    @property
    def success(self) -> bool:
        """Check if command executed successfully."""
        return self.return_code == 0 and not self.timed_out

    @property
    def output(self) -> str:
        """Get combined output, preferring stdout."""
        return self.stdout if self.stdout else self.stderr


class CommandExecutor:
    """Execute system commands asynchronously with timeout support."""

    def __init__(self, timeout: int = 10):
        """Initialize executor with default timeout."""
        self.timeout = timeout
        self.platform = Platform.detect()

    async def run(
        self,
        command: str | list[str],
        timeout: int | None = None,
        shell: bool = False,
    ) -> CommandResult:
        """
        Execute a command asynchronously.

        Args:
            command: Command to execute (string for shell, list for exec)
            timeout: Override default timeout (seconds)
            shell: Whether to run in shell mode

        Returns:
            CommandResult with stdout, stderr, return code
        """
        timeout = timeout or self.timeout

        try:
            if shell or isinstance(command, str):
                # Shell execution
                cmd_str = command if isinstance(command, str) else " ".join(command)

                if self.platform == Platform.WINDOWS:
                    # Use PowerShell on Windows
                    process = await asyncio.create_subprocess_exec(
                        "powershell",
                        "-NoProfile",
                        "-NonInteractive",
                        "-Command",
                        cmd_str,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                else:
                    # Use shell on Unix-like systems
                    process = await asyncio.create_subprocess_shell(
                        cmd_str,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
            else:
                # Direct execution
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            # Decode output with proper encoding
            encoding = "utf-8" if self.platform.is_unix else "cp1252"
            stdout_str = stdout.decode(encoding, errors="replace").strip()
            stderr_str = stderr.decode(encoding, errors="replace").strip()

            return CommandResult(
                stdout=stdout_str,
                stderr=stderr_str,
                return_code=process.returncode or 0,
            )

        except asyncio.TimeoutError:
            # Kill the process on timeout
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass

            return CommandResult(
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                return_code=-1,
                timed_out=True,
            )

        except Exception as e:
            return CommandResult(
                stdout="",
                stderr=str(e),
                return_code=-1,
            )

    async def run_powershell(self, command: str, timeout: int | None = None) -> CommandResult:
        """
        Run a PowerShell command (Windows only, no-op on other platforms).

        Args:
            command: PowerShell command to execute
            timeout: Override default timeout

        Returns:
            CommandResult
        """
        if self.platform != Platform.WINDOWS:
            return CommandResult(
                stdout="",
                stderr="PowerShell is only available on Windows",
                return_code=-1,
            )

        return await self.run(command, timeout=timeout, shell=True)

    async def run_bash(self, command: str, timeout: int | None = None) -> CommandResult:
        """
        Run a bash command (Unix only, no-op on Windows).

        Args:
            command: Bash command to execute
            timeout: Override default timeout

        Returns:
            CommandResult
        """
        if not self.platform.is_unix:
            return CommandResult(
                stdout="",
                stderr="Bash is only available on Unix-like systems",
                return_code=-1,
            )

        return await self.run(command, timeout=timeout, shell=True)

    def get_platform_command(
        self,
        macos_cmd: str | list[str],
        windows_cmd: str | list[str],
        linux_cmd: str | list[str] | None = None,
    ) -> str | list[str]:
        """
        Get the appropriate command for the current platform.

        Args:
            macos_cmd: Command for macOS
            windows_cmd: Command for Windows
            linux_cmd: Command for Linux (defaults to macOS command)

        Returns:
            Platform-appropriate command
        """
        if self.platform == Platform.MACOS:
            return macos_cmd
        elif self.platform == Platform.WINDOWS:
            return windows_cmd
        elif self.platform == Platform.LINUX:
            return linux_cmd or macos_cmd
        else:
            raise RuntimeError(f"Unsupported platform: {self.platform}")


# Global executor instance
_executor: CommandExecutor | None = None


def get_executor(timeout: int = 10) -> CommandExecutor:
    """Get or create global command executor."""
    global _executor
    if _executor is None:
        _executor = CommandExecutor(timeout=timeout)
    return _executor


def get_platform() -> Platform:
    """Get the current platform."""
    return Platform.detect()

