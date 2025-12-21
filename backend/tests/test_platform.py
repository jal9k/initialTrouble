"""Tests for platform detection and command execution."""

import pytest
from backend.diagnostics.platform import Platform, CommandExecutor, get_platform


class TestPlatform:
    """Tests for Platform enum."""

    def test_detect_returns_valid_platform(self):
        """Platform.detect() should return a valid Platform."""
        platform = Platform.detect()
        assert isinstance(platform, Platform)
        assert platform != Platform.UNKNOWN

    def test_is_unix_property(self):
        """is_unix should be True for macOS and Linux."""
        assert Platform.MACOS.is_unix is True
        assert Platform.LINUX.is_unix is True
        assert Platform.WINDOWS.is_unix is False


class TestCommandExecutor:
    """Tests for CommandExecutor."""

    @pytest.mark.asyncio
    async def test_run_simple_command(self):
        """Should execute a simple command successfully."""
        executor = CommandExecutor()
        result = await executor.run("echo hello", shell=True)
        
        assert result.success
        assert "hello" in result.stdout.lower()

    @pytest.mark.asyncio
    async def test_run_with_timeout(self):
        """Should handle timeout correctly."""
        executor = CommandExecutor(timeout=1)
        
        # This should timeout
        result = await executor.run("sleep 10", shell=True, timeout=1)
        
        assert result.timed_out
        assert not result.success

    @pytest.mark.asyncio
    async def test_run_failing_command(self):
        """Should handle failing commands."""
        executor = CommandExecutor()
        result = await executor.run("exit 1", shell=True)
        
        assert not result.success
        assert result.return_code != 0

    def test_get_platform_command(self):
        """Should return correct command for platform."""
        executor = CommandExecutor()
        
        cmd = executor.get_platform_command(
            macos_cmd="ifconfig",
            windows_cmd="ipconfig",
        )
        
        if executor.platform == Platform.WINDOWS:
            assert cmd == "ipconfig"
        else:
            assert cmd == "ifconfig"


def test_get_platform():
    """get_platform() should return current platform."""
    platform = get_platform()
    assert isinstance(platform, Platform)
    assert platform == Platform.detect()


