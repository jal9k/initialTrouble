"""Bluetooth control diagnostic - enable, disable, or check Bluetooth status.

Cross-platform tool for managing Bluetooth adapter state.
"""

from typing import Any, Literal

from .base import BaseDiagnostic, DiagnosticResult
from .platform import Platform


class ToggleBluetooth(BaseDiagnostic):
    """Enable, disable, or check Bluetooth adapter status."""

    name = "toggle_bluetooth"
    description = "Control Bluetooth adapter power state"
    osi_layer = "Physical/Link"

    async def run(
        self,
        action: Literal["on", "off", "status"] = "status",
        interface: str | None = None,
    ) -> DiagnosticResult:
        """
        Toggle Bluetooth adapter or check status.

        Args:
            action: "on" to enable, "off" to disable, "status" to check current state
            interface: Specific Bluetooth adapter (optional, uses default if not specified)

        Returns:
            DiagnosticResult with Bluetooth status
        """
        if action not in ("on", "off", "status"):
            return self._failure(
                error=f"Invalid action: {action}. Must be 'on', 'off', or 'status'",
                suggestions=["Use action='on', action='off', or action='status'"],
            )

        if self.platform == Platform.MACOS:
            return await self._run_macos(action, interface)
        elif self.platform == Platform.WINDOWS:
            return await self._run_windows(action, interface)
        elif self.platform == Platform.LINUX:
            return await self._run_linux(action, interface)
        else:
            return self._failure(
                error=f"Unsupported platform: {self.platform.value}",
                suggestions=["This tool supports macOS, Windows, and Linux"],
            )

    async def _run_macos(
        self, action: str, interface: str | None
    ) -> DiagnosticResult:
        """Control Bluetooth on macOS using blueutil."""
        # Check if blueutil is available
        check_cmd = "which blueutil"
        check_result = await self.executor.run(check_cmd, shell=True)

        if not check_result.success or not check_result.stdout.strip():
            # Try system_profiler as fallback for status
            if action == "status":
                return await self._macos_status_fallback()
            return self._failure(
                error="blueutil is not installed",
                suggestions=[
                    "Install blueutil using: brew install blueutil",
                    "blueutil is required to control Bluetooth on macOS",
                ],
            )

        if action == "status":
            # Get current Bluetooth power state
            result = await self.executor.run("blueutil --power", shell=True)
            
            if not result.success:
                return self._failure(
                    error="Failed to get Bluetooth status",
                    raw_output=result.stderr,
                )

            power_state = result.stdout.strip()
            is_on = power_state == "1"

            return self._success(
                data={
                    "bluetooth_enabled": is_on,
                    "state": "on" if is_on else "off",
                    "action": "status",
                    "changed": False,
                },
                raw_output=result.stdout,
            )

        elif action == "on":
            # Check current state first
            current = await self.executor.run("blueutil --power", shell=True)
            was_on = current.stdout.strip() == "1"

            if was_on:
                return self._success(
                    data={
                        "bluetooth_enabled": True,
                        "state": "on",
                        "action": "on",
                        "changed": False,
                        "previous_state": "on",
                    },
                    suggestions=["Bluetooth was already enabled"],
                )

            # Enable Bluetooth
            result = await self.executor.run("blueutil --power 1", shell=True)
            if not result.success:
                return self._failure(
                    error="Failed to enable Bluetooth",
                    raw_output=result.stderr,
                    suggestions=["You may need administrator privileges"],
                )

            # Verify the change
            verify = await self.executor.run("blueutil --power", shell=True)
            is_now_on = verify.stdout.strip() == "1"

            return self._success(
                data={
                    "bluetooth_enabled": is_now_on,
                    "state": "on" if is_now_on else "off",
                    "action": "on",
                    "changed": is_now_on,
                    "previous_state": "off",
                },
                suggestions=["Bluetooth has been enabled"] if is_now_on else None,
            )

        else:  # action == "off"
            # Check current state first
            current = await self.executor.run("blueutil --power", shell=True)
            was_on = current.stdout.strip() == "1"

            if not was_on:
                return self._success(
                    data={
                        "bluetooth_enabled": False,
                        "state": "off",
                        "action": "off",
                        "changed": False,
                        "previous_state": "off",
                    },
                    suggestions=["Bluetooth was already disabled"],
                )

            # Disable Bluetooth
            result = await self.executor.run("blueutil --power 0", shell=True)
            if not result.success:
                return self._failure(
                    error="Failed to disable Bluetooth",
                    raw_output=result.stderr,
                    suggestions=["You may need administrator privileges"],
                )

            # Verify the change
            verify = await self.executor.run("blueutil --power", shell=True)
            is_now_off = verify.stdout.strip() == "0"

            return self._success(
                data={
                    "bluetooth_enabled": not is_now_off,
                    "state": "off" if is_now_off else "on",
                    "action": "off",
                    "changed": is_now_off,
                    "previous_state": "on",
                },
                suggestions=["Bluetooth has been disabled"] if is_now_off else None,
            )

    async def _macos_status_fallback(self) -> DiagnosticResult:
        """Get Bluetooth status on macOS without blueutil using system_profiler."""
        cmd = "system_profiler SPBluetoothDataType 2>/dev/null | grep -i 'State:'"
        result = await self.executor.run(cmd, shell=True)

        if result.success and result.stdout:
            is_on = "on" in result.stdout.lower()
            return self._success(
                data={
                    "bluetooth_enabled": is_on,
                    "state": "on" if is_on else "off",
                    "action": "status",
                    "changed": False,
                    "note": "Status only - install blueutil to enable/disable",
                },
                raw_output=result.stdout,
                suggestions=[
                    "Install blueutil to enable/disable Bluetooth: brew install blueutil"
                ],
            )

        return self._failure(
            error="Could not determine Bluetooth status",
            suggestions=[
                "Install blueutil: brew install blueutil",
                "Check System Preferences > Bluetooth manually",
            ],
        )

    async def _run_windows(
        self, action: str, interface: str | None
    ) -> DiagnosticResult:
        """Control Bluetooth on Windows using PowerShell."""
        if action == "status":
            # Get Bluetooth adapter status
            cmd = """
            $adapter = Get-PnpDevice -Class Bluetooth -Status OK -ErrorAction SilentlyContinue | 
                Where-Object { $_.FriendlyName -match 'Bluetooth' -or $_.FriendlyName -match 'Radio' } | 
                Select-Object -First 1
            if ($adapter) {
                @{
                    Enabled = $true
                    Name = $adapter.FriendlyName
                    Status = $adapter.Status
                } | ConvertTo-Json
            } else {
                $disabled = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | 
                    Where-Object { $_.Status -eq 'Error' -or $_.Status -eq 'Disabled' } | 
                    Select-Object -First 1
                if ($disabled) {
                    @{
                        Enabled = $false
                        Name = $disabled.FriendlyName
                        Status = $disabled.Status
                    } | ConvertTo-Json
                } else {
                    @{ Enabled = $null; Name = $null; Status = 'Not Found' } | ConvertTo-Json
                }
            }
            """
            result = await self.executor.run(cmd, shell=True)

            if not result.success:
                return self._failure(
                    error="Failed to get Bluetooth status",
                    raw_output=result.stderr,
                )

            # Parse JSON output
            import json
            try:
                data = json.loads(result.stdout)
                is_on = data.get("Enabled", False)
            except json.JSONDecodeError:
                is_on = "OK" in result.stdout

            return self._success(
                data={
                    "bluetooth_enabled": is_on,
                    "state": "on" if is_on else "off",
                    "action": "status",
                    "changed": False,
                },
                raw_output=result.stdout,
            )

        elif action == "on":
            # Enable Bluetooth adapter
            cmd = """
            $adapter = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | 
                Where-Object { $_.FriendlyName -match 'Bluetooth' -or $_.FriendlyName -match 'Radio' } | 
                Select-Object -First 1
            if ($adapter) {
                Enable-PnpDevice -InstanceId $adapter.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
                $updated = Get-PnpDevice -InstanceId $adapter.InstanceId
                @{
                    Success = ($updated.Status -eq 'OK')
                    Name = $adapter.FriendlyName
                    Status = $updated.Status
                } | ConvertTo-Json
            } else {
                @{ Success = $false; Error = 'No Bluetooth adapter found' } | ConvertTo-Json
            }
            """
            result = await self.executor.run(cmd, shell=True, timeout=30)

            if not result.success:
                return self._failure(
                    error="Failed to enable Bluetooth",
                    raw_output=result.stderr,
                    suggestions=[
                        "Administrator privileges may be required",
                        "Run as Administrator to enable Bluetooth",
                    ],
                )

            return self._success(
                data={
                    "bluetooth_enabled": True,
                    "state": "on",
                    "action": "on",
                    "changed": True,
                    "previous_state": "off",
                },
                raw_output=result.stdout,
                suggestions=["Bluetooth has been enabled"],
            )

        else:  # action == "off"
            # Disable Bluetooth adapter
            cmd = """
            $adapter = Get-PnpDevice -Class Bluetooth -Status OK -ErrorAction SilentlyContinue | 
                Where-Object { $_.FriendlyName -match 'Bluetooth' -or $_.FriendlyName -match 'Radio' } | 
                Select-Object -First 1
            if ($adapter) {
                Disable-PnpDevice -InstanceId $adapter.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
                $updated = Get-PnpDevice -InstanceId $adapter.InstanceId
                @{
                    Success = ($updated.Status -ne 'OK')
                    Name = $adapter.FriendlyName
                    Status = $updated.Status
                } | ConvertTo-Json
            } else {
                @{ Success = $false; Error = 'No enabled Bluetooth adapter found' } | ConvertTo-Json
            }
            """
            result = await self.executor.run(cmd, shell=True, timeout=30)

            if not result.success:
                return self._failure(
                    error="Failed to disable Bluetooth",
                    raw_output=result.stderr,
                    suggestions=[
                        "Administrator privileges may be required",
                        "Run as Administrator to disable Bluetooth",
                    ],
                )

            return self._success(
                data={
                    "bluetooth_enabled": False,
                    "state": "off",
                    "action": "off",
                    "changed": True,
                    "previous_state": "on",
                },
                raw_output=result.stdout,
                suggestions=["Bluetooth has been disabled"],
            )

    async def _run_linux(
        self, action: str, interface: str | None
    ) -> DiagnosticResult:
        """Control Bluetooth on Linux using rfkill."""
        if action == "status":
            # Check Bluetooth status using rfkill
            cmd = "rfkill list bluetooth 2>/dev/null || rfkill list | grep -i bluetooth"
            result = await self.executor.run(cmd, shell=True)

            if not result.success or not result.stdout.strip():
                return self._failure(
                    error="Could not get Bluetooth status",
                    suggestions=[
                        "Verify rfkill is installed",
                        "Check if Bluetooth hardware is present",
                    ],
                )

            # Parse rfkill output
            output_lower = result.stdout.lower()
            soft_blocked = "soft blocked: yes" in output_lower
            hard_blocked = "hard blocked: yes" in output_lower
            is_on = not soft_blocked and not hard_blocked

            return self._success(
                data={
                    "bluetooth_enabled": is_on,
                    "state": "on" if is_on else "off",
                    "soft_blocked": soft_blocked,
                    "hard_blocked": hard_blocked,
                    "action": "status",
                    "changed": False,
                },
                raw_output=result.stdout,
                suggestions=["Hardware switch is blocking Bluetooth"] if hard_blocked else None,
            )

        elif action == "on":
            # Unblock Bluetooth
            cmd = "rfkill unblock bluetooth"
            result = await self.executor.run(cmd, shell=True)

            if not result.success:
                return self._failure(
                    error="Failed to enable Bluetooth",
                    raw_output=result.stderr,
                    suggestions=[
                        "You may need sudo privileges: sudo rfkill unblock bluetooth",
                        "Check if Bluetooth hardware is present",
                    ],
                )

            # Optionally start bluetooth service
            await self.executor.run(
                "systemctl start bluetooth 2>/dev/null || service bluetooth start 2>/dev/null",
                shell=True,
            )

            # Verify
            verify = await self.executor.run("rfkill list bluetooth", shell=True)
            is_on = "soft blocked: no" in verify.stdout.lower()

            return self._success(
                data={
                    "bluetooth_enabled": is_on,
                    "state": "on" if is_on else "off",
                    "action": "on",
                    "changed": True,
                    "previous_state": "off",
                },
                raw_output=result.stdout + "\n" + verify.stdout,
                suggestions=["Bluetooth has been enabled"] if is_on else None,
            )

        else:  # action == "off"
            # Block Bluetooth
            cmd = "rfkill block bluetooth"
            result = await self.executor.run(cmd, shell=True)

            if not result.success:
                return self._failure(
                    error="Failed to disable Bluetooth",
                    raw_output=result.stderr,
                    suggestions=[
                        "You may need sudo privileges: sudo rfkill block bluetooth",
                    ],
                )

            # Verify
            verify = await self.executor.run("rfkill list bluetooth", shell=True)
            is_off = "soft blocked: yes" in verify.stdout.lower()

            return self._success(
                data={
                    "bluetooth_enabled": not is_off,
                    "state": "off" if is_off else "on",
                    "action": "off",
                    "changed": True,
                    "previous_state": "on",
                },
                raw_output=result.stdout + "\n" + verify.stdout,
                suggestions=["Bluetooth has been disabled"] if is_off else None,
            )


# Module-level function for easy importing
async def toggle_bluetooth(
    action: Literal["on", "off", "status"] = "status",
    interface: str | None = None,
) -> DiagnosticResult:
    """Toggle Bluetooth adapter or check status.
    
    Args:
        action: "on" to enable, "off" to disable, "status" to check
        interface: Specific Bluetooth adapter (optional)
        
    Returns:
        DiagnosticResult with Bluetooth status
    """
    diag = ToggleBluetooth()
    return await diag.run(action=action, interface=interface)

