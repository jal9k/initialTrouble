# Function: repair_office365

## Purpose

Repair Microsoft 365 installation to fix application issues like crashes, missing features, activation problems, or corrupted installations. Supports both Quick Repair (local, faster) and Online Repair (downloads fresh components, more thorough).

## OSI Layer

**Application Layer** - Manages application repair and configuration.

## When to Use

- Office apps crash frequently or won't open
- Features are missing or broken
- Office activation issues
- "Office needs to be repaired" messages
- After Windows updates break Office
- User says: "Word crashes", "Excel won't open", "Office not working", "activation failed"

## Platform

**Windows only** - This tool uses Windows-specific Office repair mechanisms.

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| repair_type | string | No | "quick" | Type of repair: "quick" (local) or "online" (cloud) |
| apps_to_repair | list | No | None | Specific apps to target (informational only, repair affects all Office apps) |

## Output Schema

```python
class RepairOffice365Result(BaseModel):
    """Result data specific to repair_office365."""
    
    office_version: str = Field(description="Detected Office version")
    office_product: str = Field(description="Product IDs (e.g., 'O365ProPlusRetail')")
    installation_type: str = Field(description="'ClickToRun' or 'MSI'")
    repair_type_used: str = Field(description="'quick' or 'online'")
    repair_initiated: bool = Field(description="Whether repair was started")
    apps_closed: list[str] = Field(description="Office apps that were closed")
```

## Implementation Details

### Step 1: Detect Office Installation

```powershell
# Check Click-to-Run configuration
Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration'

# Returns:
# - VersionToReport: e.g., "16.0.17328.20282"
# - ProductReleaseIds: e.g., "O365ProPlusRetail"
# - Platform: "x64" or "x86"
# - UpdateChannel: e.g., "Current"
```

### Step 2: Check Installation Type

- **Click-to-Run**: Modern subscription Office (Microsoft 365, Office 2019+)
- **MSI**: Volume license installations (Office 2016, 2019 volume)

MSI installations require different repair method:
```powershell
msiexec /fa {ProductCode}
```

### Step 3: Close Office Applications

```powershell
# Close all Office apps before repair
Stop-Process -Name WINWORD, EXCEL, POWERPNT, OUTLOOK, MSACCESS, ONENOTE, MSPUB, lync, Teams -Force
```

### Step 4: Run Repair

**Quick Repair:**
```powershell
# Fast local repair (~10-15 minutes)
Start-Process -FilePath "C:\Program Files\Microsoft Office\root\Client\OfficeClickToRun.exe" `
    -ArgumentList "scenario=Repair platform=x64 culture=en-us"
```

**Online Repair:**
```powershell
# Full cloud repair (~30-60 minutes)
Start-Process -FilePath "C:\Program Files\Microsoft Office\root\Client\OfficeClickToRun.exe" `
    -ArgumentList "scenario=Repair platform=x64 culture=en-us RepairType=2"
```

## Repair Types Comparison

| Aspect | Quick Repair | Online Repair |
|--------|--------------|---------------|
| Duration | 10-15 minutes | 30-60 minutes |
| Network | Not required | Required |
| Thoroughness | Fixes common issues | Complete reinstall of components |
| Downloads | None | ~2-4 GB |
| When to Use | First attempt | When quick repair fails |

## Error Handling

| Error Condition | Detection | Suggested Action |
|-----------------|-----------|------------------|
| Office not installed | Registry key missing | Install Office first |
| MSI installation | Wrong installation type | Use Programs and Features |
| OfficeClickToRun.exe not found | Path doesn't exist | Office may be corrupted, reinstall |
| Repair fails to start | Exit code != 0 | Run as Administrator |
| Apps still running | Lock errors | Close all Office apps manually |

## Example Output

### Success Case (Quick Repair)

```json
{
    "success": true,
    "function_name": "repair_office365",
    "platform": "windows",
    "data": {
        "office_version": "16.0.17328.20282",
        "office_product": "O365ProPlusRetail",
        "installation_type": "ClickToRun",
        "repair_type_used": "quick",
        "repair_initiated": true,
        "apps_closed": ["WINWORD", "OUTLOOK"]
    },
    "raw_output": "",
    "error": null,
    "suggestions": [
        "Office repair has been initiated",
        "Quick repair typically takes 10-15 minutes",
        "If issues persist, try 'online' repair for a more thorough fix",
        "Restart your computer after repair completes"
    ]
}
```

### Office Not Installed

```json
{
    "success": false,
    "function_name": "repair_office365",
    "platform": "windows",
    "data": {
        "detection_attempted": true
    },
    "raw_output": "",
    "error": "Microsoft Office not detected",
    "suggestions": [
        "Microsoft 365 or Office does not appear to be installed",
        "If Office is installed, it may be an MSI installation (not Click-to-Run)",
        "For MSI installations, use Programs and Features to repair"
    ]
}
```

### MSI Installation Detected

```json
{
    "success": false,
    "function_name": "repair_office365",
    "platform": "windows",
    "data": {
        "office_version": "MSI Installation"
    },
    "raw_output": "",
    "error": "MSI-based Office installation detected",
    "suggestions": [
        "This tool supports Click-to-Run Office installations",
        "For MSI installations: Control Panel > Programs > Repair",
        "Or run: msiexec /fa {ProductCode}"
    ]
}
```

### Online Repair

```json
{
    "success": true,
    "function_name": "repair_office365",
    "platform": "windows",
    "data": {
        "office_version": "16.0.17328.20282",
        "office_product": "O365BusinessRetail",
        "installation_type": "ClickToRun",
        "repair_type_used": "online",
        "repair_initiated": true,
        "apps_closed": []
    },
    "raw_output": "",
    "error": null,
    "suggestions": [
        "Office repair has been initiated",
        "Online repair may take 30-60 minutes depending on internet speed",
        "This downloads fresh Office components from Microsoft",
        "Do not interrupt the repair process",
        "Restart your computer after repair completes"
    ]
}
```

## Test Cases

### Manual Testing

1. **Quick Repair**: Run quick repair on working Office, verify no issues
2. **Online Repair**: Run online repair, verify download and completion
3. **Office Not Installed**: Run on system without Office
4. **MSI Office**: Run on volume license Office 2016
5. **Apps Running**: Run while Office apps are open, verify they close

### Automated Tests

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.diagnostics.windows.office_repair import RepairOffice365

@pytest.mark.asyncio
async def test_repair_office_not_installed():
    """Test when Office is not installed."""
    diag = RepairOffice365()
    
    with patch.object(diag, '_detect_office', new_callable=AsyncMock) as mock:
        mock.return_value = {"installed": False}
        
        result = await diag.run()
        
        assert not result.success
        assert "not detected" in result.error

@pytest.mark.asyncio
async def test_repair_office_msi():
    """Test rejection of MSI installation."""
    diag = RepairOffice365()
    
    with patch.object(diag, '_detect_office', new_callable=AsyncMock) as mock:
        mock.return_value = {"installed": True, "type": "msi"}
        
        result = await diag.run()
        
        assert not result.success
        assert "MSI" in result.error

@pytest.mark.asyncio
async def test_repair_office_success():
    """Test successful repair initiation."""
    diag = RepairOffice365()
    
    with patch.object(diag, '_detect_office', new_callable=AsyncMock) as mock_detect:
        with patch.object(diag, '_close_office_apps', new_callable=AsyncMock) as mock_close:
            with patch.object(diag, '_run_repair', new_callable=AsyncMock) as mock_repair:
                mock_detect.return_value = {
                    "installed": True,
                    "type": "ClickToRun",
                    "version": "16.0.17328.20282",
                    "product": "O365ProPlusRetail"
                }
                mock_close.return_value = []
                mock_repair.return_value = {"success": True}
                
                result = await diag.run(repair_type="quick")
                
                assert result.success
                assert result.data["repair_initiated"]
```

## Implementation Notes

- Repair runs in background as it can take a long time
- Office apps are force-closed before repair starts
- Repair affects all Office apps, not just specific ones
- Online repair requires stable internet connection
- User should restart computer after repair completes

## Related Functions

- `review_system_logs`: Check for Office-related errors
- `kill_process`: Force close stubborn Office processes
- `cleanup_temp_files`: May help with some Office cache issues

