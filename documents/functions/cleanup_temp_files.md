# Function: cleanup_temp_files

## Purpose

Remove temporary files from standard cache and temp locations to free disk space and potentially resolve application issues caused by corrupted cache data.

## OSI Layer

**Application Layer** - Addresses application-level storage and caching issues.

## When to Use

- User reports disk space is running low
- Application is behaving erratically (potential corrupted cache)
- General system maintenance and cleanup
- Before or after troubleshooting application issues
- User says: "running out of space", "disk full", "app is slow", "app won't start"

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| aggressive | boolean | No | false | If true, includes additional cache locations like browser caches and trash |
| dry_run | boolean | No | false | If true, reports what would be deleted without actually deleting |

## Output Schema

```python
class CleanupTempFilesResult(BaseModel):
    """Result data specific to cleanup_temp_files."""
    
    files_deleted: int = Field(description="Number of files removed")
    space_freed_mb: float = Field(description="Megabytes of space recovered")
    space_freed_bytes: int = Field(description="Exact bytes freed")
    errors_count: int = Field(description="Number of files that couldn't be deleted")
    errors: list[str] = Field(description="First 10 error messages")
    skipped_count: int = Field(description="Files skipped (recent or protected)")
    dry_run: bool = Field(description="Whether this was a dry run")
    mode: str = Field(description="'standard' or 'aggressive'")
    paths_scanned: int = Field(description="Number of paths that were scanned")
```

## Platform-Specific Locations

### macOS

**Standard Locations:**
```bash
~/Library/Caches          # User application caches
/tmp                      # System temp directory
/var/folders/*/*/T        # Per-user temp directories
```

**Aggressive Locations (additional):**
```bash
~/Library/Logs            # Application logs
~/.Trash                  # User trash
```

**Parsing Logic:**
- Use `os.path.expanduser()` for ~ expansion
- Use `glob` for wildcard patterns
- Skip files modified within the last hour
- Check file permissions before deletion

### Windows

**Standard Locations:**
```powershell
%TEMP%                              # User temp (typically C:\Users\X\AppData\Local\Temp)
%LOCALAPPDATA%\Temp                 # Local app data temp
C:\Windows\Temp                     # System temp
```

**Aggressive Locations (additional):**
```powershell
%LOCALAPPDATA%\Microsoft\Windows\INetCache    # IE/Edge cache
```

**Parsing Logic:**
- Use `os.path.expandvars()` for environment variable expansion
- May require administrator privileges for Windows\Temp
- Skip files in use (locked by other processes)

### Linux

**Standard Locations:**
```bash
/tmp                      # System temp
/var/tmp                  # Persistent temp
~/.cache                  # User cache (XDG standard)
```

**Aggressive Locations (additional):**
```bash
~/.local/share/Trash      # User trash (XDG standard)
```

**Parsing Logic:**
- Follow XDG Base Directory Specification
- Respect file permissions
- Skip files owned by other users (unless root)

## Safety Considerations

1. **Never delete files modified within the last hour** - They may be in use
2. **Skip protected directories** - Never clean /, /bin, /usr, ~/Documents, etc.
3. **Handle permission errors gracefully** - Report but don't fail
4. **Log all deletions** - For potential recovery reference
5. **Support dry run** - Let users preview before deletion
6. **Don't follow symlinks** - Avoid accidentally deleting linked content

## Error Handling

| Error Condition | Detection | Suggested Action |
|-----------------|-----------|------------------|
| Permission denied | PermissionError exception | Run as administrator/root |
| File in use | Windows: sharing violation | Skip file, try again later |
| Path not found | FileNotFoundError | Skip silently (expected on some systems) |
| Disk I/O error | IOError | Report error, continue with other files |

## Example Output

### Success Case (Standard Mode)

```json
{
    "success": true,
    "function_name": "cleanup_temp_files",
    "platform": "macos",
    "data": {
        "files_deleted": 1247,
        "space_freed_mb": 523.45,
        "space_freed_bytes": 548798464,
        "errors_count": 3,
        "errors": [
            "Permission denied: /tmp/locked_file",
            "Permission denied: ~/Library/Caches/system.cache"
        ],
        "skipped_count": 45,
        "dry_run": false,
        "mode": "standard",
        "paths_scanned": 3
    },
    "raw_output": "",
    "error": null,
    "suggestions": [
        "Significant space recovered. Consider running cleanup regularly."
    ]
}
```

### Dry Run Case

```json
{
    "success": true,
    "function_name": "cleanup_temp_files",
    "platform": "windows",
    "data": {
        "files_deleted": 892,
        "space_freed_mb": 234.12,
        "space_freed_bytes": 245489664,
        "errors_count": 0,
        "errors": [],
        "skipped_count": 12,
        "dry_run": true,
        "mode": "standard",
        "paths_scanned": 3
    },
    "raw_output": "",
    "error": null,
    "suggestions": [
        "This was a dry run. Run with dry_run=False to actually delete files."
    ]
}
```

### Minimal Cleanup Case

```json
{
    "success": true,
    "function_name": "cleanup_temp_files",
    "platform": "linux",
    "data": {
        "files_deleted": 23,
        "space_freed_mb": 4.5,
        "space_freed_bytes": 4718592,
        "errors_count": 0,
        "errors": [],
        "skipped_count": 5,
        "dry_run": false,
        "mode": "standard",
        "paths_scanned": 3
    },
    "raw_output": "",
    "error": null,
    "suggestions": [
        "Minimal temp files found. Your system is already fairly clean."
    ]
}
```

## Test Cases

### Manual Testing

1. **Happy Path**: Run on a system with temp files, verify files are removed
2. **Dry Run**: Run with dry_run=True, verify no files are deleted
3. **Aggressive Mode**: Run with aggressive=True, verify additional locations are cleaned
4. **Permission Test**: Create files without delete permission, verify error handling
5. **Recent Files**: Create file just now, verify it's skipped
6. **Cross-Platform**: Run on macOS, Windows, and Linux

### Automated Tests

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
from backend.diagnostics.temp_files import CleanupTempFiles

@pytest.mark.asyncio
async def test_cleanup_temp_files_dry_run():
    """Test that dry run doesn't delete files."""
    diag = CleanupTempFiles()
    
    # Create a mock file
    mock_file = MagicMock()
    mock_file.is_file.return_value = True
    mock_file.stat.return_value.st_mtime = 0  # Old file
    mock_file.stat.return_value.st_size = 1024
    
    with patch.object(Path, 'rglob', return_value=[mock_file]):
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'is_dir', return_value=True):
                result = await diag.run(dry_run=True)
    
    assert result.success
    assert result.data["dry_run"] == True
    mock_file.unlink.assert_not_called()

@pytest.mark.asyncio
async def test_cleanup_temp_files_skips_recent():
    """Test that recently modified files are skipped."""
    diag = CleanupTempFiles()
    
    import time
    mock_file = MagicMock()
    mock_file.is_file.return_value = True
    mock_file.stat.return_value.st_mtime = time.time()  # Just now
    mock_file.stat.return_value.st_size = 1024
    
    with patch.object(Path, 'rglob', return_value=[mock_file]):
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'is_dir', return_value=True):
                result = await diag.run(dry_run=False)
    
    assert result.success
    assert result.data["skipped_count"] > 0

@pytest.mark.asyncio
async def test_cleanup_temp_files_aggressive_mode():
    """Test aggressive mode includes additional paths."""
    diag = CleanupTempFiles()
    
    standard_paths = diag._get_paths(aggressive=False)
    aggressive_paths = diag._get_paths(aggressive=True)
    
    assert len(aggressive_paths) > len(standard_paths)
```

## Implementation Notes

- Uses `pathlib.Path` for cross-platform path handling
- Runs asynchronously to avoid blocking on large directories
- Implements a 1-hour safety window for recent files
- Limits error output to prevent overwhelming the user
- Returns detailed statistics for both deleted and skipped files

## Related Functions

- `kill_process`: May need to kill processes holding file locks
- `get_ip_config`: Not directly related, but disk space can affect system performance
- `review_system_logs`: Logs may be cleaned in aggressive mode

