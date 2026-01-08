"""WiFi control diagnostic - enable/disable WiFi adapter.

This module provides tools to control the WiFi adapter state.
"""

from typing import Any

from .base import BaseDiagnostic, DiagnosticResult
from .platform import Platform


class EnableWifi(BaseDiagnostic):
    """Enable the WiFi adapter."""

    name = "enable_wifi"
    description = "Enable WiFi adapter"
    osi_layer = "Physical/Link"

    async def run(self, interface_name: str | None = None) -> DiagnosticResult:
        """
        Enable WiFi adapter.

        Args:
            interface_name: Specific WiFi interface to enable (optional)
                           macOS default: en0, Windows default: Wi-Fi

        Returns:
            DiagnosticResult with operation status
        """
        if self.platform == Platform.MACOS:
            return await self._run_macos(interface_name)
        elif self.platform == Platform.WINDOWS:
            return await self._run_windows(interface_name)
        else:
            return self._failure(
                error=f"Unsupported platform: {self.platform.value}",
                suggestions=["This tool only supports macOS and Windows"],
            )

    async def _run_macos(self, interface_name: str | None) -> DiagnosticResult:
        """Enable WiFi on macOS using networksetup."""
        interface = interface_name or "en0"

        # First, check current WiFi power status
        check_cmd = f"networksetup -getairportpower {interface}"
        check_result = await self.executor.run(check_cmd, shell=True)

        if not check_result.success:
            return self._failure(
                error=f"Failed to check WiFi status for interface {interface}",
                raw_output=check_result.stderr,
                suggestions=[
                    f"Verify that '{interface}' is a valid WiFi interface",
                    "Run 'networksetup -listallhardwareports' to find WiFi interface",
                ],
            )

        # Check if WiFi is already on
        if "On" in check_result.stdout:
            return self._success(
                data={
                    "interface": interface,
                    "action": "enable_wifi",
                    "previous_state": "on",
                    "current_state": "on",
                    "changed": False,
                },
                raw_output=check_result.stdout,
                suggestions=["WiFi was already enabled"],
            )

        # Turn WiFi on
        enable_cmd = f"networksetup -setairportpower {interface} on"
        enable_result = await self.executor.run(enable_cmd, shell=True)

        if not enable_result.success:
            return self._failure(
                error=f"Failed to enable WiFi on interface {interface}",
                raw_output=enable_result.stderr,
                suggestions=[
                    "You may need administrator privileges to enable WiFi",
                    "Try running with sudo or from an admin account",
                ],
            )

        # Verify the change
        verify_result = await self.executor.run(check_cmd, shell=True)
        current_state = "on" if "On" in verify_result.stdout else "off"

        if current_state == "on":
            return self._success(
                data={
                    "interface": interface,
                    "action": "enable_wifi",
                    "previous_state": "off",
                    "current_state": "on",
                    "changed": True,
                },
                raw_output=verify_result.stdout,
                suggestions=[
                    "WiFi has been enabled successfully",
                    "You may need to connect to a WiFi network manually",
                    "Use 'check_adapter_status' to verify connection",
                ],
            )
        else:
            return self._failure(
                error="WiFi enable command succeeded but state did not change",
                raw_output=verify_result.stdout,
                suggestions=[
                    "WiFi hardware switch may be disabled",
                    "Check System Preferences > Network for WiFi status",
                ],
            )

    async def _run_windows(self, interface_name: str | None) -> DiagnosticResult:
        """Enable WiFi on Windows using netsh."""
        interface = interface_name or "Wi-Fi"

        # Check current state
        check_cmd = f'netsh interface show interface name="{interface}"'
        check_result = await self.executor.run(check_cmd, shell=True)

        if not check_result.success:
            return self._failure(
                error=f"Failed to check WiFi status for interface '{interface}'",
                raw_output=check_result.stderr,
                suggestions=[
                    f"Verify that '{interface}' is a valid WiFi interface",
                    "Run 'netsh interface show interface' to list available interfaces",
                ],
            )

        # Determine previous state from output
        if "Enabled" in check_result.stdout or "Connected" in check_result.stdout:
            previous_state = "on"
        elif "Disabled" in check_result.stdout:
            previous_state = "off"
        else:
            previous_state = "off"  # Default to off if state unclear

        if previous_state == "on":
            return self._success(
                data={
                    "interface": interface,
                    "action": "enable_wifi",
                    "previous_state": "on",
                    "current_state": "on",
                    "changed": False,
                },
                raw_output=check_result.stdout,
                suggestions=["WiFi adapter was already enabled"],
            )

        # Enable the interface
        enable_cmd = f'netsh interface set interface "{interface}" enable'
        enable_result = await self.executor.run(enable_cmd, shell=True)

        if not enable_result.success:
            return self._failure(
                error=f"Failed to enable WiFi interface '{interface}'",
                raw_output=enable_result.stderr,
                suggestions=[
                    "Administrator privileges may be required",
                    "Run command prompt as Administrator",
                    f"Verify interface name with: netsh interface show interface",
                ],
            )

        # Verify the change
        verify_result = await self.executor.run(check_cmd, shell=True)
        current_state = "on" if ("Enabled" in verify_result.stdout or "Connected" in verify_result.stdout) else "off"

        if current_state == "on":
            return self._success(
                data={
                    "interface": interface,
                    "action": "enable_wifi",
                    "previous_state": previous_state,
                    "current_state": "on",
                    "changed": True,
                },
                raw_output=verify_result.stdout,
                suggestions=[
                    "WiFi adapter has been enabled successfully",
                    "You may need to connect to a WiFi network",
                    "Use 'check_adapter_status' to verify connection",
                ],
            )
        else:
            return self._failure(
                error="WiFi enable command succeeded but adapter state did not change",
                raw_output=verify_result.stdout,
                suggestions=[
                    "Check if WiFi hardware switch is enabled on your device",
                    "Open Network & Internet settings to verify WiFi status",
                ],
            )


# Module-level function for easy importing
async def enable_wifi(interface_name: str | None = None, interface: str | None = None) -> DiagnosticResult:
    """Enable WiFi adapter."""
    # Accept both 'interface' and 'interface_name' for LLM compatibility
    iface = interface or interface_name
    diag = EnableWifi()
    return await diag.run(interface_name=iface)

