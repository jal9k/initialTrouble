# Function: fix_dell_audio

## Purpose

Fix Dell audio driver issues by removing and reinstalling the audio device driver. This is a common fix for Dell computers where the Realtek or Waves MaxxAudio driver becomes corrupted or conflicts with Windows updates.

## OSI Layer

**Application Layer** - Manages hardware driver configuration.

## When to Use

- User reports no audio on a Dell computer
- Audio was working but stopped after Windows update
- Audio devices show as "not working" in Device Manager
- Realtek or Waves MaxxAudio driver issues
- User says: "no sound on Dell", "audio stopped working", "speakers not detected"

## Platform

**Windows only** - This tool uses Windows-specific device management commands.

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| confirm_reboot | boolean | No | false | If true, automatically initiate reboot after driver removal |
| backup_driver | boolean | No | true | If true, export current driver info before removal |

## Output Schema

```python
class FixDellAudioResult(BaseModel):
    """Result data specific to fix_dell_audio."""
    
    is_dell: bool = Field(description="Whether system was verified as Dell")
    devices_found: int = Field(description="Number of Dell audio devices detected")
    devices_removed: list[str] = Field(description="Names of devices that were removed")
    removed_count: int = Field(description="Number of devices successfully removed")
    failed_count: int = Field(description="Number of devices that failed to remove")
    driver_backed_up: bool = Field(description="Whether driver was backed up")
    backup_path: str | None = Field(description="Path to driver backup")
    reboot_required: bool = Field(description="Whether reboot is needed (always true)")
    reboot_initiated: bool = Field(description="Whether auto-reboot was triggered")
```

## Implementation Details

### Step 1: Verify Dell System

```powershell
# Check BIOS manufacturer
Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object Manufacturer
```

Only proceed if manufacturer contains "Dell".

### Step 2: Find Dell Audio Devices

```powershell
# Find audio endpoint and media devices
Get-PnpDevice -Class AudioEndpoint, Media | 
    Where-Object {$_.FriendlyName -match 'Realtek|Waves|MaxxAudio|Dell Audio'} |
    Select-Object InstanceId, FriendlyName, Class, Status
```

### Step 3: Backup Driver (Optional)

```powershell
# Export driver information
pnputil /export-driver "oem123.inf" C:\DriverBackup

# Or simpler: export device info
$device | Export-Clixml -Path "$env:TEMP\dell_audio_backup.xml"
```

### Step 4: Remove Device

```powershell
# Disable device first
Disable-PnpDevice -InstanceId $instanceId -Confirm:$false

# Remove device
pnputil /remove-device $instanceId
```

### Step 5: Initiate Reboot (if confirmed)

```powershell
# Schedule reboot in 60 seconds
shutdown /r /t 60 /c "Rebooting to reinstall audio drivers"

# To cancel: shutdown /a
```

## Safety Considerations

1. **Verify Dell hardware** - Only run on Dell computers
2. **Backup driver first** - Create export before removal
3. **Warn about audio loss** - Audio will be unavailable until reboot
4. **Never force reboot** - Give user time to save work (60 second delay)
5. **Provide cancellation option** - Show how to cancel scheduled reboot

## Error Handling

| Error Condition | Detection | Suggested Action |
|-----------------|-----------|------------------|
| Not a Dell system | Manufacturer check fails | Suggest manual Device Manager fix |
| No audio devices found | Empty device list | Device may already be removed |
| Permission denied | Device removal fails | Run as Administrator |
| Device in use | Lock error | Close audio applications first |

## Example Output

### Success Case

```json
{
    "success": true,
    "function_name": "fix_dell_audio",
    "platform": "windows",
    "data": {
        "is_dell": true,
        "devices_found": 2,
        "devices_removed": [
            "Realtek High Definition Audio",
            "Waves MaxxAudio Pro"
        ],
        "removed_count": 2,
        "failed_count": 0,
        "driver_backed_up": true,
        "backup_path": "C:\\Users\\User\\AppData\\Local\\Temp\\dell_audio_driver_backup",
        "reboot_required": true,
        "reboot_initiated": false
    },
    "raw_output": "",
    "error": null,
    "suggestions": [
        "Successfully removed 2 audio device(s)",
        "Please restart your computer to reinstall the audio driver",
        "Windows will automatically install a generic driver on reboot",
        "If audio still doesn't work after reboot, download the latest driver from Dell support"
    ]
}
```

### Not a Dell System

```json
{
    "success": false,
    "function_name": "fix_dell_audio",
    "platform": "windows",
    "data": {
        "manufacturer_check": "failed"
    },
    "raw_output": "",
    "error": "This does not appear to be a Dell system",
    "suggestions": [
        "This tool is designed for Dell computers",
        "For other manufacturers, try Device Manager manually"
    ]
}
```

### Auto-Reboot Case

```json
{
    "success": true,
    "function_name": "fix_dell_audio",
    "platform": "windows",
    "data": {
        "is_dell": true,
        "devices_found": 1,
        "devices_removed": ["Realtek High Definition Audio"],
        "removed_count": 1,
        "failed_count": 0,
        "driver_backed_up": true,
        "backup_path": "C:\\...",
        "reboot_required": true,
        "reboot_initiated": true
    },
    "raw_output": "",
    "error": null,
    "suggestions": [
        "Successfully removed 1 audio device(s)",
        "System will reboot in 60 seconds. Save your work!",
        "To cancel reboot, run: shutdown /a"
    ]
}
```

## Test Cases

### Manual Testing

1. **Dell System**: Run on Dell computer, verify device removal
2. **Non-Dell System**: Run on non-Dell, verify appropriate error
3. **No Devices**: Run when audio device already removed
4. **Permission Test**: Run without admin, verify error message
5. **Backup Verification**: Check backup file is created

### Automated Tests

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.diagnostics.windows.dell_audio import FixDellAudio

@pytest.mark.asyncio
async def test_fix_dell_audio_non_windows():
    """Test rejection on non-Windows platform."""
    from backend.diagnostics.platform import Platform
    
    diag = FixDellAudio()
    diag._platform = Platform.MACOS
    
    result = await diag.run()
    
    assert not result.success
    assert "Windows" in result.error

@pytest.mark.asyncio
async def test_fix_dell_audio_non_dell():
    """Test rejection on non-Dell system."""
    diag = FixDellAudio()
    
    with patch.object(diag, '_verify_dell_system', new_callable=AsyncMock) as mock:
        mock.return_value = False
        
        result = await diag.run()
        
        assert not result.success
        assert "Dell" in result.error

@pytest.mark.asyncio
async def test_fix_dell_audio_success():
    """Test successful driver removal."""
    diag = FixDellAudio()
    
    with patch.object(diag, '_verify_dell_system', new_callable=AsyncMock) as mock_dell:
        with patch.object(diag, '_find_audio_devices', new_callable=AsyncMock) as mock_find:
            with patch.object(diag, '_backup_driver', new_callable=AsyncMock) as mock_backup:
                with patch.object(diag, '_remove_device', new_callable=AsyncMock) as mock_remove:
                    mock_dell.return_value = True
                    mock_find.return_value = [{"instance_id": "123", "name": "Realtek Audio"}]
                    mock_backup.return_value = "C:\\backup"
                    mock_remove.return_value = True
                    
                    result = await diag.run()
                    
                    assert result.success
                    assert result.data["removed_count"] == 1
```

## Implementation Notes

- Uses `Get-PnpDevice` for device enumeration
- Uses `pnputil` for device removal (more reliable than PowerShell cmdlets)
- Driver backup is informational (full driver export requires admin and more complex commands)
- Reboot is scheduled with 60-second delay to allow user to save work
- After reboot, Windows will automatically install a generic audio driver

## Related Functions

- `review_system_logs`: Check for audio-related errors in Event Viewer
- `run_dism_sfc`: May help if system files are corrupted
- `kill_process`: May need to close audio applications first

