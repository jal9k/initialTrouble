# Function: run_dism_sfc

## Purpose

Repair Windows system file corruption using DISM (Deployment Image Servicing and Management) and SFC (System File Checker). These tools repair the Windows component store and system files respectively.

## OSI Layer

**Application Layer** - Repairs operating system files and components.

## When to Use

- Windows is behaving erratically
- Applications fail with missing DLL errors
- Windows Update fails repeatedly
- Blue screens with system file corruption hints
- After malware removal
- User says: "Windows corrupted", "missing DLL", "system files damaged"

## Platform

**Windows only** - DISM and SFC are Windows-specific utilities.

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| run_dism | boolean | No | true | Run DISM /RestoreHealth first |
| run_sfc | boolean | No | true | Run SFC /scannow after DISM |
| check_only | boolean | No | false | Only scan for issues, don't repair |

## Output Schema

```python
class RunDismSfcResult(BaseModel):
    """Result data specific to run_dism_sfc."""
    
    dism_result: str = Field(description="DISM result: healthy, repaired, unrepairable, error")
    dism_issues_found: int = Field(description="Number of issues detected by DISM")
    dism_issues_fixed: int = Field(description="Number of issues repaired by DISM")
    sfc_result: str = Field(description="SFC result: no_violations, repaired, unrepairable, error")
    sfc_files_repaired: list[str] = Field(description="List of files repaired by SFC")
    reboot_required: bool = Field(description="Whether repairs require reboot")
    logs: dict = Field(description="Paths to log files")
```

## Implementation Details

### DISM Commands

```powershell
# Quick health check
DISM /Online /Cleanup-Image /CheckHealth

# Thorough scan (takes longer)
DISM /Online /Cleanup-Image /ScanHealth

# Repair component store
DISM /Online /Cleanup-Image /RestoreHealth
```

DISM repairs the Windows component store, which contains copies of all Windows system files. If the component store is corrupted, SFC won't be able to repair damaged files.

### SFC Command

```powershell
# Scan and repair system files
sfc /scannow

# Verify only (no repair)
sfc /verifyonly
```

SFC compares system files against the component store and replaces corrupted files.

### Execution Order

1. **Run DISM first** - Repairs component store
2. **Then run SFC** - Uses repaired component store to fix system files
3. **Check logs** - Review CBS.log and DISM.log for details

## Log Locations

| Log | Path | Purpose |
|-----|------|---------|
| DISM Log | `%WINDIR%\Logs\DISM\dism.log` | DISM operation details |
| CBS Log | `%WINDIR%\Logs\CBS\CBS.log` | SFC results and file details |

## Result Meanings

### DISM Results

| Result | Meaning |
|--------|---------|
| `healthy` | No corruption detected |
| `repaired` | Corruption found and fixed |
| `unrepairable` | Corruption found but couldn't fix (may need reinstall) |
| `error` | DISM failed to run |

### SFC Results

| Result | Meaning |
|--------|---------|
| `no_violations` | All system files are intact |
| `repaired` | Found and repaired corrupt files |
| `unrepairable` | Found files that couldn't be repaired |
| `error` | SFC failed to run |

## Error Handling

| Error Condition | Detection | Suggested Action |
|-----------------|-----------|------------------|
| Not Administrator | Privilege check fails | Run as Administrator |
| DISM timeout | Command exceeds 30 min | Try Safe Mode or WinRE |
| DISM source missing | RestoreHealth fails | Use /Source with Windows ISO |
| SFC pending reboot | "pending repair" message | Restart and run again |
| Unrepairable files | Specific error in CBS.log | May need in-place upgrade |

## Example Output

### Healthy System

```json
{
    "success": true,
    "function_name": "run_dism_sfc",
    "platform": "windows",
    "data": {
        "dism_result": "healthy",
        "dism_issues_found": 0,
        "dism_issues_fixed": 0,
        "sfc_result": "no_violations",
        "sfc_files_repaired": [],
        "reboot_required": false,
        "logs": {
            "dism_log": "%WINDIR%\\Logs\\DISM\\dism.log",
            "cbs_log": "%WINDIR%\\Logs\\CBS\\CBS.log"
        }
    },
    "raw_output": "",
    "error": null,
    "suggestions": [
        "System files are healthy. No repairs were needed."
    ]
}
```

### Successful Repair

```json
{
    "success": true,
    "function_name": "run_dism_sfc",
    "platform": "windows",
    "data": {
        "dism_result": "repaired",
        "dism_issues_found": 3,
        "dism_issues_fixed": 3,
        "sfc_result": "repaired",
        "sfc_files_repaired": [
            "C:\\Windows\\System32\\ntdll.dll",
            "C:\\Windows\\System32\\kernel32.dll"
        ],
        "reboot_required": true,
        "logs": {
            "dism_log": "%WINDIR%\\Logs\\DISM\\dism.log",
            "cbs_log": "%WINDIR%\\Logs\\CBS\\CBS.log"
        }
    },
    "raw_output": "",
    "error": null,
    "suggestions": [
        "System file repairs were successful.",
        "Please restart your computer to complete the repairs.",
        "A restart is required to apply all changes."
    ]
}
```

### Unrepairable Corruption

```json
{
    "success": false,
    "function_name": "run_dism_sfc",
    "platform": "windows",
    "data": {
        "dism_result": "repaired",
        "dism_issues_found": 2,
        "dism_issues_fixed": 2,
        "sfc_result": "unrepairable",
        "sfc_files_repaired": [],
        "reboot_required": false,
        "logs": {
            "dism_log": "%WINDIR%\\Logs\\DISM\\dism.log",
            "cbs_log": "%WINDIR%\\Logs\\CBS\\CBS.log"
        }
    },
    "raw_output": "",
    "error": "Some corruption could not be repaired",
    "suggestions": [
        "Some corruption could not be automatically repaired.",
        "Consider running an in-place upgrade repair or reset Windows.",
        "Check the CBS.log for details: %WINDIR%\\Logs\\CBS\\CBS.log"
    ]
}
```

### Administrator Required

```json
{
    "success": false,
    "function_name": "run_dism_sfc",
    "platform": "windows",
    "data": {},
    "raw_output": "",
    "error": "Administrator privileges required",
    "suggestions": [
        "Run as Administrator to use this tool",
        "Right-click the application and select 'Run as administrator'",
        "Or open an elevated PowerShell prompt"
    ]
}
```

## Test Cases

### Manual Testing

1. **Healthy System**: Run on clean Windows, verify no issues found
2. **Check Only**: Run with check_only=true, verify no repairs made
3. **DISM Only**: Run with run_sfc=false, verify only DISM runs
4. **SFC Only**: Run with run_dism=false, verify only SFC runs
5. **Non-Admin**: Run without admin, verify appropriate error

### Automated Tests

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.diagnostics.windows.system_repair import RunDismSfc

@pytest.mark.asyncio
async def test_run_dism_sfc_not_admin():
    """Test rejection when not running as admin."""
    diag = RunDismSfc()
    
    with patch.object(diag, '_check_admin', new_callable=AsyncMock) as mock:
        mock.return_value = False
        
        result = await diag.run()
        
        assert not result.success
        assert "Administrator" in result.error

@pytest.mark.asyncio
async def test_run_dism_sfc_healthy():
    """Test healthy system detection."""
    diag = RunDismSfc()
    
    with patch.object(diag, '_check_admin', new_callable=AsyncMock) as mock_admin:
        with patch.object(diag, '_run_dism', new_callable=AsyncMock) as mock_dism:
            with patch.object(diag, '_run_sfc', new_callable=AsyncMock) as mock_sfc:
                mock_admin.return_value = True
                mock_dism.return_value = {"dism_result": "healthy", "dism_issues_found": 0, "dism_issues_fixed": 0}
                mock_sfc.return_value = {"sfc_result": "no_violations", "sfc_files_repaired": [], "reboot_required": False, "logs": {}}
                
                result = await diag.run()
                
                assert result.success
                assert result.data["dism_result"] == "healthy"
```

## Implementation Notes

- DISM can take 10-30 minutes depending on system
- SFC typically takes 10-20 minutes
- Both require Administrator privileges
- Running from Safe Mode or WinRE may help with stubborn issues
- For DISM failures, can use Windows ISO as source:
  `DISM /Online /Cleanup-Image /RestoreHealth /Source:D:\Sources\install.wim`

## Related Functions

- `review_system_logs`: Check for corruption-related errors
- `repair_office365`: Office has its own repair mechanism
- `fix_dell_audio`: For driver-specific issues

