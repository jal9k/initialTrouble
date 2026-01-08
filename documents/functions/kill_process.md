# Function: kill_process

## Purpose

Terminate problematic processes that are hung, consuming excessive resources, or interfering with system operation. Includes safety guards to prevent killing critical system processes.

## OSI Layer

**Application Layer** - Manages application-level process control.

## When to Use

- User reports an application is frozen or unresponsive
- A process is consuming excessive CPU or memory
- An application won't close normally
- System is sluggish due to a runaway process
- User says: "app frozen", "program stuck", "can't close", "high CPU usage"

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| process_name | string | No* | None | Name of process to kill (e.g., "chrome", "Teams"). Case-insensitive partial match. |
| process_id | integer | No* | None | Specific PID to terminate |
| force | boolean | No | false | Use forceful termination (SIGKILL/-9 on Unix, /Force on Windows) |
| include_children | boolean | No | true | Also terminate child processes |

*Note: Either `process_name` or `process_id` must be provided.

## Output Schema

```python
class KillProcessResult(BaseModel):
    """Result data specific to kill_process."""
    
    killed: list[dict] = Field(description="Processes that were successfully terminated")
    killed_count: int = Field(description="Number of processes killed")
    failed: list[dict] = Field(description="Processes that could not be terminated")
    failed_count: int = Field(description="Number of processes that failed to terminate")
    protected_blocked: list[dict] = Field(description="Protected processes that were blocked")
    protected_blocked_count: int = Field(description="Number of protected processes blocked")
    force_used: bool = Field(description="Whether forceful termination was used")
```

## Platform-Specific Implementation

### macOS

**Find processes:**
```bash
# By name (case-insensitive)
ps aux | grep -i 'processname' | grep -v grep

# By PID
ps -p 1234 -o pid=,comm=
```

**Kill commands:**
```bash
# Graceful termination (SIGTERM)
kill -TERM 1234

# Forceful termination (SIGKILL)
kill -9 1234
```

**Protected Processes:**
- kernel_task, launchd, WindowServer, loginwindow
- opendirectoryd, securityd, diskarbitrationd
- configd, mds, mds_stores, notifyd, UserEventAgent

### Windows

**Find processes:**
```powershell
# By name (wildcard match)
Get-Process -Name '*chrome*' | Select-Object Id, ProcessName | ConvertTo-Json

# By PID
Get-Process -Id 1234 | Select-Object Id, ProcessName | ConvertTo-Json
```

**Kill commands:**
```powershell
# Graceful termination
Stop-Process -Id 1234

# Forceful termination
Stop-Process -Id 1234 -Force
```

**Protected Processes:**
- System, smss.exe, csrss.exe, wininit.exe
- services.exe, lsass.exe, svchost.exe, winlogon.exe
- dwm.exe, RuntimeBroker.exe, fontdrvhost.exe

### Linux

**Find processes:**
```bash
# By name
ps aux | grep -i 'processname' | grep -v grep

# By PID
ps -p 1234 -o pid=,comm=
```

**Kill commands:**
```bash
# Graceful termination
kill -TERM 1234

# Forceful termination  
kill -9 1234
```

**Protected Processes:**
- init, systemd, kthreadd, dbus-daemon
- NetworkManager, gdm, sddm, lightdm
- Xorg, gnome-shell, plasmashell, journald

## Safety Considerations

1. **Protected process list** - Critical system processes are NEVER killed
2. **Graceful first** - Default to SIGTERM, use SIGKILL only when requested
3. **Verification** - Confirm process termination after kill attempt
4. **Clear reporting** - Show what was killed vs blocked vs failed
5. **No wildcards on system processes** - Never match protected processes by pattern

## Error Handling

| Error Condition | Detection | Suggested Action |
|-----------------|-----------|------------------|
| No process found | Empty process list | Check spelling, verify process is running |
| Permission denied | Kill command fails | Run as administrator/root |
| Protected process | Matched in protected list | Explain why, suggest alternative |
| Process won't die | Still running after kill | Try force=true, may need reboot |
| Invalid PID | PID doesn't exist | Process may have already terminated |

## Example Output

### Success Case

```json
{
    "success": true,
    "function_name": "kill_process",
    "platform": "macos",
    "data": {
        "killed": [
            {"pid": 12345, "name": "Google Chrome Helper"},
            {"pid": 12346, "name": "Google Chrome"}
        ],
        "killed_count": 2,
        "failed": [],
        "failed_count": 0,
        "protected_blocked": [],
        "protected_blocked_count": 0,
        "force_used": false
    },
    "raw_output": "",
    "error": null,
    "suggestions": [
        "Successfully terminated 2 process(es)"
    ]
}
```

### Protected Process Blocked

```json
{
    "success": false,
    "function_name": "kill_process",
    "platform": "windows",
    "data": {
        "protected_blocked": [
            {"pid": 4, "name": "System"},
            {"pid": 876, "name": "svchost"}
        ],
        "protected_blocked_count": 2
    },
    "raw_output": "",
    "error": "All matching processes are protected system processes",
    "suggestions": [
        "These processes are critical for system operation",
        "Killing them would likely crash or destabilize the system",
        "If the system is unresponsive, consider a restart instead"
    ]
}
```

### Process Not Found

```json
{
    "success": false,
    "function_name": "kill_process",
    "platform": "linux",
    "data": {
        "search_name": "nonexistent_app",
        "search_pid": null
    },
    "raw_output": "",
    "error": "No matching processes found",
    "suggestions": [
        "Check the process name spelling",
        "Use Task Manager (Windows) or Activity Monitor (macOS) to find the correct name",
        "The process may have already terminated"
    ]
}
```

### Permission Denied

```json
{
    "success": false,
    "function_name": "kill_process",
    "platform": "macos",
    "data": {
        "failed": [
            {"pid": 1, "name": "launchd"}
        ],
        "failed_count": 1
    },
    "raw_output": "",
    "error": "Failed to terminate any processes",
    "suggestions": [
        "Try running with force=True for forceful termination",
        "You may need administrator/root privileges",
        "The process may be stuck in an uninterruptible state"
    ]
}
```

## Test Cases

### Manual Testing

1. **Happy Path**: Start a test app, kill it by name, verify it's gone
2. **By PID**: Get PID of a process, kill by PID
3. **Protected Process**: Try to kill "System" or "launchd", verify blocked
4. **Force Kill**: Use force=true on a stubborn process
5. **Not Found**: Try to kill a non-existent process
6. **Cross-Platform**: Test on macOS, Windows, and Linux

### Automated Tests

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.diagnostics.process_mgmt import KillProcess

@pytest.mark.asyncio
async def test_kill_process_requires_identifier():
    """Test that either name or PID is required."""
    diag = KillProcess()
    result = await diag.run()
    
    assert not result.success
    assert "Must specify" in result.error

@pytest.mark.asyncio
async def test_kill_process_blocks_protected():
    """Test that protected processes are blocked."""
    diag = KillProcess()
    
    with patch.object(diag, '_find_processes', new_callable=AsyncMock) as mock_find:
        mock_find.return_value = [{"pid": 1, "name": "launchd"}]
        
        result = await diag.run(process_name="launchd")
        
        assert not result.success
        assert "protected" in result.error.lower()

@pytest.mark.asyncio
async def test_kill_process_success():
    """Test successful process termination."""
    diag = KillProcess()
    
    with patch.object(diag, '_find_processes', new_callable=AsyncMock) as mock_find:
        with patch.object(diag, '_kill_process', new_callable=AsyncMock) as mock_kill:
            mock_find.return_value = [{"pid": 12345, "name": "test_app"}]
            mock_kill.return_value = True
            
            result = await diag.run(process_name="test_app")
            
            assert result.success
            assert result.data["killed_count"] == 1
```

## Implementation Notes

- Process name matching is case-insensitive and uses partial matching
- On Unix systems, uses `ps` and `kill` commands
- On Windows, uses PowerShell `Get-Process` and `Stop-Process`
- Protected process list is checked by partial name match for safety
- Verification is performed after kill to confirm termination

## Related Functions

- `cleanup_temp_files`: Killing processes may be needed to unlock files
- `review_system_logs`: Can help identify why a process became unresponsive
- `check_adapter_status`: Some network processes may need to be restarted

