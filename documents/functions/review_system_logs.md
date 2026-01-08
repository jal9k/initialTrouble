# Function: review_system_logs

## Purpose

Analyze Windows system logs to identify the cause of crashes, blue screens (BSOD), and system errors. Consolidates information from Event Viewer, crash dumps, and Reliability Monitor into an actionable report.

## OSI Layer

**Application Layer** - Analyzes operating system diagnostics and logs.

## When to Use

- System crashes or freezes frequently
- Blue screen errors occur
- Need to diagnose recurring issues
- After unexpected shutdowns
- User says: "keeps crashing", "blue screen", "computer restarts randomly", "won't stay on"

## Platform

**Windows only** - Analyzes Windows-specific log sources.

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| log_types | list | No | all | Which logs to analyze. Options: "event_viewer", "crash_dumps", "bsod", "reliability" |
| time_range_hours | integer | No | 72 | How far back to search in hours |
| severity_filter | string | No | "error" | Minimum severity. Options: "info", "warning", "error", "critical" |

## Output Schema

```python
class ReviewSystemLogsResult(BaseModel):
    """Result data specific to review_system_logs."""
    
    analysis_period: str = Field(description="Time range analyzed")
    critical_events: list[dict] = Field(description="Critical severity events")
    error_events: list[dict] = Field(description="Error severity events")
    warning_events: list[dict] = Field(description="Warning severity events")
    crash_dumps_found: int = Field(description="Number of crash dumps found")
    crash_dump_details: list[dict] = Field(description="Details of crash dumps")
    bsod_events: list[dict] = Field(description="Blue screen events with codes")
    reliability_score: float | None = Field(description="Windows stability index 1-10")
    top_issues: list[dict] = Field(description="Ranked list of most frequent issues")
    recommendations: list[str] = Field(description="Suggested actions")
```

## Log Sources

### Event Viewer

```powershell
# Query System and Application logs for errors
Get-WinEvent -FilterHashtable @{
    LogName = 'System', 'Application'
    Level = 1,2,3  # Critical, Error, Warning
    StartTime = (Get-Date).AddHours(-72)
} -MaxEvents 100
```

**Key Event IDs:**
| Source | Event ID | Meaning |
|--------|----------|---------|
| Kernel-Power | 41 | Unexpected shutdown |
| BugCheck | 1001 | Blue screen occurred |
| WHEA-Logger | 18,19 | Hardware errors |
| Disk | 7,11 | Disk errors |
| NTFS | 55,98 | File system errors |

### Crash Dumps

**Locations:**
- `%LOCALAPPDATA%\CrashDumps\` - Application crash dumps
- `C:\Windows\Minidump\` - Kernel minidumps (BSOD)
- `C:\Windows\MEMORY.DMP` - Full memory dump

### BSOD Analysis

```powershell
# Get BugCheck events from System log
Get-WinEvent -FilterHashtable @{
    LogName = 'System'
    ProviderName = 'Microsoft-Windows-WER-SystemErrorReporting'
    Id = 1001
}
```

### Reliability Monitor

```powershell
# Get reliability stability index
Get-CimInstance -ClassName Win32_ReliabilityStabilityMetrics |
    Select-Object SystemStabilityIndex
```

**Stability Index:**
- 10.0 = Perfect (no failures)
- 7-9 = Good
- 5-6 = Moderate issues
- Below 5 = Significant problems

## Common BSOD Codes

| Code | Likely Cause |
|------|--------------|
| DRIVER_IRQL_NOT_LESS_OR_EQUAL | Driver issue - outdated or faulty |
| PAGE_FAULT_IN_NONPAGED_AREA | RAM issue or driver problem |
| SYSTEM_SERVICE_EXCEPTION | Driver or system file corruption |
| KMODE_EXCEPTION_NOT_HANDLED | Driver compatibility issue |
| NTFS_FILE_SYSTEM | Disk or file system corruption |
| KERNEL_DATA_INPAGE_ERROR | Hard drive or memory failure |
| CRITICAL_PROCESS_DIED | Critical system process crashed |
| DPC_WATCHDOG_VIOLATION | Storage driver issue (usually SSD) |
| WHEA_UNCORRECTABLE_ERROR | Hardware error - CPU, RAM, motherboard |
| MEMORY_MANAGEMENT | RAM or virtual memory issue |

## Error Handling

| Error Condition | Detection | Suggested Action |
|-----------------|-----------|------------------|
| Access denied | Event log query fails | Run as Administrator |
| No events found | Empty results | Expand time range |
| Log service stopped | Query timeout | Start Event Log service |

## Example Output

### Multiple Issues Found

```json
{
    "success": true,
    "function_name": "review_system_logs",
    "platform": "windows",
    "data": {
        "analysis_period": "Last 72 hours",
        "critical_events": [
            {
                "time": "2024-12-22 15:30:45",
                "level": "Critical",
                "source": "Kernel-Power",
                "id": 41,
                "message": "The system has rebooted without cleanly shutting down..."
            }
        ],
        "error_events": [
            {
                "time": "2024-12-22 15:30:00",
                "level": "Error",
                "source": "Microsoft-Windows-WER-SystemErrorReporting",
                "id": 1001,
                "message": "The computer has rebooted from a bugcheck..."
            }
        ],
        "warning_events": [],
        "crash_dumps_found": 2,
        "crash_dump_details": [
            {
                "path": "C:\\Windows\\Minidump\\122224-12345-01.dmp",
                "name": "122224-12345-01.dmp",
                "size": 286720,
                "created": "2024-12-22 15:30:45"
            }
        ],
        "bsod_events": [
            {
                "time": "2024-12-22 15:30:00",
                "code": "DRIVER_IRQL_NOT_LESS_OR_EQUAL",
                "message": "The computer has rebooted from a bugcheck...",
                "likely_cause": "Driver issue - outdated or faulty driver"
            }
        ],
        "reliability_score": 4.2,
        "top_issues": [
            {
                "type": "BSOD",
                "code": "DRIVER_IRQL_NOT_LESS_OR_EQUAL",
                "count": 3,
                "severity": "critical",
                "cause": "Driver issue - outdated or faulty driver"
            },
            {
                "type": "Error",
                "source": "Disk",
                "count": 5,
                "severity": "error"
            }
        ],
        "recommendations": [
            "Found 3 blue screen event(s). Review driver updates.",
            "BSOD cause: Driver issue - outdated or faulty driver",
            "Found 2 crash dump(s). Consider analyzing with WinDbg or BlueScreenView.",
            "System stability score is low (4.2/10). Consider system repair or driver updates."
        ]
    },
    "raw_output": "",
    "error": null,
    "suggestions": [
        "Found 3 blue screen event(s). Review driver updates.",
        "BSOD cause: Driver issue - outdated or faulty driver",
        "Found 2 crash dump(s). Consider analyzing with WinDbg or BlueScreenView.",
        "System stability score is low (4.2/10). Consider system repair or driver updates.",
        "Found 1 critical event(s). These require immediate attention."
    ]
}
```

### Clean System

```json
{
    "success": true,
    "function_name": "review_system_logs",
    "platform": "windows",
    "data": {
        "analysis_period": "Last 72 hours",
        "critical_events": [],
        "error_events": [],
        "warning_events": [],
        "crash_dumps_found": 0,
        "crash_dump_details": [],
        "bsod_events": [],
        "reliability_score": 9.5,
        "top_issues": [],
        "recommendations": [
            "System stability score is good (9.5/10).",
            "No significant issues found in system logs."
        ]
    },
    "raw_output": "",
    "error": null,
    "suggestions": [
        "System stability score is good (9.5/10).",
        "No significant issues found in system logs."
    ]
}
```

## Test Cases

### Manual Testing

1. **Clean System**: Run on stable system, verify low issue count
2. **After BSOD**: Run after intentional crash, verify BSOD detection
3. **Time Range**: Test with different time_range_hours values
4. **Severity Filter**: Test each severity level filter
5. **Specific Log Types**: Test each log_type individually

### Automated Tests

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.diagnostics.windows.log_analysis import ReviewSystemLogs

@pytest.mark.asyncio
async def test_review_system_logs_clean():
    """Test analysis of clean system."""
    diag = ReviewSystemLogs()
    
    with patch.object(diag, '_analyze_event_viewer', new_callable=AsyncMock) as mock_ev:
        with patch.object(diag, '_analyze_crash_dumps', new_callable=AsyncMock) as mock_dumps:
            with patch.object(diag, '_analyze_bsod', new_callable=AsyncMock) as mock_bsod:
                with patch.object(diag, '_get_reliability_score', new_callable=AsyncMock) as mock_rel:
                    mock_ev.return_value = {"critical": [], "error": [], "warning": []}
                    mock_dumps.return_value = {"count": 0, "details": []}
                    mock_bsod.return_value = []
                    mock_rel.return_value = 9.5
                    
                    result = await diag.run()
                    
                    assert result.success
                    assert result.data["reliability_score"] == 9.5
                    assert len(result.data["bsod_events"]) == 0

@pytest.mark.asyncio
async def test_review_system_logs_bsod():
    """Test BSOD detection."""
    diag = ReviewSystemLogs()
    
    with patch.object(diag, '_analyze_event_viewer', new_callable=AsyncMock) as mock_ev:
        with patch.object(diag, '_analyze_crash_dumps', new_callable=AsyncMock) as mock_dumps:
            with patch.object(diag, '_analyze_bsod', new_callable=AsyncMock) as mock_bsod:
                with patch.object(diag, '_get_reliability_score', new_callable=AsyncMock) as mock_rel:
                    mock_ev.return_value = {"critical": [], "error": [], "warning": []}
                    mock_dumps.return_value = {"count": 1, "details": []}
                    mock_bsod.return_value = [{"code": "DRIVER_IRQL_NOT_LESS_OR_EQUAL", "time": "2024-12-22"}]
                    mock_rel.return_value = 4.0
                    
                    result = await diag.run()
                    
                    assert result.success
                    assert len(result.data["bsod_events"]) == 1
                    assert "driver" in result.data["recommendations"][0].lower()
```

## Implementation Notes

- Queries are limited to prevent excessive processing time
- BSOD codes are mapped to human-readable causes
- Reliability score is from Windows Reliability Monitor
- Crash dump analysis provides locations but doesn't parse dump contents
- For detailed dump analysis, recommend WinDbg or BlueScreenView

## Related Functions

- `run_dism_sfc`: Repair system files if corruption detected
- `fix_dell_audio`: If audio driver is identified as cause
- `kill_process`: Terminate problematic processes

