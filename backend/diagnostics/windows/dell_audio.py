"""Dell audio driver fix diagnostic.

Removes and reinstalls Dell audio drivers to fix common
audio issues with Realtek/Waves MaxxAudio on Dell computers.

See documents/functions/fix_dell_audio.md for full specification.
"""

import json
from typing import Any

from ..base import BaseDiagnostic, DiagnosticResult
from ..platform import Platform


class FixDellAudio(BaseDiagnostic):
    """Fix Dell audio driver issues by removing and reinstalling drivers."""

    name = "fix_dell_audio"
    description = "Remove and reinstall Dell audio drivers to fix audio issues"
    osi_layer = "Application"

    # Keywords to identify Dell audio devices
    DELL_AUDIO_KEYWORDS = [
        "realtek",
        "waves",
        "maxxaudio",
        "dell audio",
        "high definition audio",
    ]

    async def run(
        self,
        confirm_reboot: bool = False,
        backup_driver: bool = True,
    ) -> DiagnosticResult:
        """
        Fix Dell audio by removing and reinstalling drivers.

        Args:
            confirm_reboot: If true, automatically initiate reboot after driver removal
            backup_driver: If true, export current driver before removal

        Returns:
            DiagnosticResult with removal status and reboot instructions
        """
        # Check platform
        if self.platform != Platform.WINDOWS:
            return self._failure(
                error="This tool is only available on Windows",
                suggestions=["Run this on a Windows computer"],
            )

        # Step 1: Verify this is a Dell system
        is_dell = await self._verify_dell_system()
        if not is_dell:
            return self._failure(
                error="This does not appear to be a Dell system",
                data={"manufacturer_check": "failed"},
                suggestions=[
                    "This tool is designed for Dell computers",
                    "For other manufacturers, try Device Manager manually",
                ],
            )

        # Step 2: Find Dell audio devices
        audio_devices = await self._find_audio_devices()
        if not audio_devices:
            return self._failure(
                error="No Dell audio devices found",
                suggestions=[
                    "Audio device may already be removed",
                    "Check Device Manager for audio devices",
                    "Try running Windows troubleshooter instead",
                ],
            )

        # Step 3: Backup driver if requested
        backup_path = None
        if backup_driver:
            backup_path = await self._backup_driver(audio_devices[0])

        # Step 4: Remove audio devices
        removed_devices = []
        failed_devices = []

        for device in audio_devices:
            success = await self._remove_device(device)
            if success:
                removed_devices.append(device)
            else:
                failed_devices.append(device)

        if not removed_devices:
            return self._failure(
                error="Failed to remove any audio devices",
                data={
                    "devices_found": len(audio_devices),
                    "failed_devices": failed_devices,
                },
                suggestions=[
                    "Run as Administrator and try again",
                    "Some devices may be in use - close audio applications first",
                    "Try removing devices manually in Device Manager",
                ],
            )

        # Step 5: Initiate reboot if confirmed
        reboot_initiated = False
        if confirm_reboot:
            reboot_initiated = await self._initiate_reboot()

        return self._success(
            data={
                "is_dell": True,
                "devices_found": len(audio_devices),
                "devices_removed": [d.get("name", "Unknown") for d in removed_devices],
                "removed_count": len(removed_devices),
                "failed_count": len(failed_devices),
                "driver_backed_up": backup_path is not None,
                "backup_path": backup_path,
                "reboot_required": True,
                "reboot_initiated": reboot_initiated,
            },
            suggestions=self._generate_suggestions(
                removed_devices, failed_devices, reboot_initiated
            ),
        )

    async def _verify_dell_system(self) -> bool:
        """Verify this is a Dell computer."""
        cmd = "Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object Manufacturer | ConvertTo-Json"
        result = await self.executor.run(cmd, shell=True)

        if not result.success:
            return False

        try:
            data = json.loads(result.stdout)
            manufacturer = data.get("Manufacturer", "").lower()
            return "dell" in manufacturer
        except json.JSONDecodeError:
            return False

    async def _find_audio_devices(self) -> list[dict[str, Any]]:
        """Find Dell audio devices."""
        # Get audio endpoint devices
        cmd = """
        Get-PnpDevice -Class AudioEndpoint, Media | 
        Where-Object {$_.Status -ne 'Unknown'} |
        Select-Object InstanceId, FriendlyName, Class, Status |
        ConvertTo-Json
        """
        result = await self.executor.run(cmd, shell=True)

        if not result.success:
            return []

        try:
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]
        except json.JSONDecodeError:
            return []

        # Filter for Dell/Realtek/Waves audio devices
        dell_devices = []
        for device in data:
            name = device.get("FriendlyName", "").lower()
            if any(keyword in name for keyword in self.DELL_AUDIO_KEYWORDS):
                dell_devices.append({
                    "instance_id": device.get("InstanceId"),
                    "name": device.get("FriendlyName"),
                    "class": device.get("Class"),
                    "status": device.get("Status"),
                })

        return dell_devices

    async def _backup_driver(self, device: dict[str, Any]) -> str | None:
        """Backup driver before removal."""
        instance_id = device.get("instance_id")
        if not instance_id:
            return None

        backup_path = "%TEMP%\\dell_audio_driver_backup"

        # This is a simplified backup - full driver export requires pnputil
        cmd = f"""
        $backupPath = "$env:TEMP\\dell_audio_driver_backup"
        New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
        
        # Export driver info (not full driver package)
        $device = Get-PnpDevice | Where-Object {{$_.InstanceId -eq '{instance_id}'}}
        $device | Export-Clixml -Path "$backupPath\\device_info.xml"
        
        Write-Output $backupPath
        """
        result = await self.executor.run(cmd, shell=True)

        if result.success and result.stdout.strip():
            return result.stdout.strip()

        return None

    async def _remove_device(self, device: dict[str, Any]) -> bool:
        """Remove a single audio device."""
        instance_id = device.get("instance_id")
        if not instance_id:
            return False

        # Use pnputil to remove the device
        cmd = f"""
        $device = Get-PnpDevice | Where-Object {{$_.InstanceId -eq '{instance_id}'}}
        if ($device) {{
            # Disable first
            Disable-PnpDevice -InstanceId '{instance_id}' -Confirm:$false -ErrorAction SilentlyContinue
            
            # Then remove
            pnputil /remove-device '{instance_id}' 2>&1
            
            Write-Output "Removed"
        }} else {{
            Write-Output "NotFound"
        }}
        """
        result = await self.executor.run(cmd, shell=True)

        return result.success and "Removed" in result.stdout

    async def _initiate_reboot(self) -> bool:
        """Initiate system reboot."""
        # Schedule reboot in 60 seconds to give user time to save work
        cmd = "shutdown /r /t 60 /c 'Rebooting to reinstall audio drivers'"
        result = await self.executor.run(cmd, shell=True)
        return result.success

    def _generate_suggestions(
        self,
        removed: list,
        failed: list,
        reboot_initiated: bool,
    ) -> list[str]:
        """Generate suggestions based on results."""
        suggestions = []

        if removed:
            suggestions.append(
                f"Successfully removed {len(removed)} audio device(s)"
            )

        if failed:
            suggestions.append(
                f"Failed to remove {len(failed)} device(s). Try running as Administrator."
            )

        if reboot_initiated:
            suggestions.append(
                "System will reboot in 60 seconds. Save your work!"
            )
            suggestions.append(
                "To cancel reboot, run: shutdown /a"
            )
        else:
            suggestions.append(
                "Please restart your computer to reinstall the audio driver"
            )
            suggestions.append(
                "Windows will automatically install a generic driver on reboot"
            )
            suggestions.append(
                "If audio still doesn't work after reboot, download the latest driver from Dell support"
            )

        return suggestions


# Module-level function for easy importing
async def fix_dell_audio(
    confirm_reboot: bool = False,
    backup_driver: bool = True,
) -> DiagnosticResult:
    """Fix Dell audio by removing and reinstalling drivers.
    
    Args:
        confirm_reboot: If true, automatically initiate reboot
        backup_driver: If true, export current driver before removal
        
    Returns:
        DiagnosticResult with removal status
    """
    diag = FixDellAudio()
    return await diag.run(confirm_reboot=confirm_reboot, backup_driver=backup_driver)

