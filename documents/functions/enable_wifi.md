# Function: enable_wifi

## Purpose

Enable the WiFi adapter on the system. Use this when WiFi is disabled and needs to be turned on to restore network connectivity.

## OSI Layer

**Layer 1 (Physical) / Layer 2 (Data Link)** - Controls the network interface hardware state.

## When to Use

- When `check_adapter_status` shows WiFi is disabled (status: down)
- When user reports WiFi is turned off
- As a remediation step after diagnosing that WiFi adapter is disabled
- Before attempting to connect to a WiFi network

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| interface_name | string | No | en0 (macOS) / Wi-Fi (Windows) | Specific WiFi interface to enable. Only specify if default doesn't work. |

## Output Schema

```python
from pydantic import BaseModel, Field
from typing import Literal

class EnableWifiResult(BaseModel):
    """Result data for enable_wifi."""
    
    interface: str = Field(description="WiFi interface that was targeted")
    action: Literal["enable_wifi"] = Field(description="Action that was performed")
    previous_state: Literal["on", "off", "unknown"] = Field(
        description="WiFi state before the operation"
    )
    current_state: Literal["on", "off"] = Field(
        description="WiFi state after the operation"
    )
    changed: bool = Field(description="Whether the state actually changed")
```

## Platform Commands

### macOS

```bash
# Check current WiFi power state
networksetup -getairportpower en0

# Enable WiFi
networksetup -setairportpower en0 on

# List WiFi interfaces if en0 doesn't work
networksetup -listallhardwareports | grep -A 2 Wi-Fi
```

**Parsing Logic:**

1. Run `networksetup -getairportpower <interface>` to check current state
2. Parse output for "On" or "Off"
3. If already on, return early with `changed: false`
4. Run `networksetup -setairportpower <interface> on`
5. Verify state changed by re-running get command

**Example networksetup output:**
```
Wi-Fi Power (en0): Off
```

### Windows

```powershell
# Check interface state
netsh interface show interface name="Wi-Fi"

# Enable WiFi adapter
netsh interface set interface "Wi-Fi" enable

# Alternative: Get-NetAdapter
Get-NetAdapter -Name "Wi-Fi" | Enable-NetAdapter
```

**Parsing Logic:**

1. Run `netsh interface show interface` to check current state
2. Parse for "Enabled" or "Disabled" in output
3. If already enabled, return early with `changed: false`
4. Run `netsh interface set interface "<name>" enable`
5. Verify state changed by re-running check command

**Example netsh output:**
```
Admin State:    Enabled
Connect State:  Connected
Type:           Dedicated
Interface Name: Wi-Fi
```

## Error Handling

| Error Condition | Detection | Suggested Action |
|-----------------|-----------|------------------|
| Invalid interface | Command fails with "not found" | Run `networksetup -listallhardwareports` (macOS) or `netsh interface show interface` (Windows) to find correct name |
| Permission denied | Return code non-zero | May need admin/sudo privileges |
| Hardware switch off | Enable succeeds but state unchanged | Check physical WiFi switch on device |
| WiFi hardware absent | Interface not found | Verify device has WiFi capability |

## Example Output

### Success Case (WiFi Enabled)

```json
{
    "success": true,
    "function_name": "enable_wifi",
    "platform": "macos",
    "data": {
        "interface": "en0",
        "action": "enable_wifi",
        "previous_state": "off",
        "current_state": "on",
        "changed": true
    },
    "raw_output": "Wi-Fi Power (en0): On",
    "error": null,
    "suggestions": [
        "WiFi has been enabled successfully",
        "You may need to connect to a WiFi network manually",
        "Use 'check_adapter_status' to verify connection"
    ]
}
```

### Success Case (WiFi Already On)

```json
{
    "success": true,
    "function_name": "enable_wifi",
    "platform": "macos",
    "data": {
        "interface": "en0",
        "action": "enable_wifi",
        "previous_state": "on",
        "current_state": "on",
        "changed": false
    },
    "raw_output": "Wi-Fi Power (en0): On",
    "error": null,
    "suggestions": [
        "WiFi was already enabled"
    ]
}
```

### Failure Case (Invalid Interface)

```json
{
    "success": false,
    "function_name": "enable_wifi",
    "platform": "macos",
    "data": {},
    "raw_output": "** Error: Wi-Fi power is not supported.",
    "error": "Failed to check WiFi status for interface en5",
    "suggestions": [
        "Verify that 'en5' is a valid WiFi interface",
        "Run 'networksetup -listallhardwareports' to find WiFi interface"
    ]
}
```

### Failure Case (Permission Denied - Windows)

```json
{
    "success": false,
    "function_name": "enable_wifi",
    "platform": "windows",
    "data": {},
    "raw_output": "This operation requires elevation.",
    "error": "Failed to enable WiFi interface 'Wi-Fi'",
    "suggestions": [
        "Administrator privileges may be required",
        "Run command prompt as Administrator",
        "Verify interface name with: netsh interface show interface"
    ]
}
```

## Test Cases

### Manual Testing

1. **Happy Path**: Disable WiFi manually, run tool, verify WiFi is enabled
2. **Already Enabled**: Run with WiFi already on, verify `changed: false`
3. **Invalid Interface**: Use wrong interface name, verify helpful error
4. **Cross-Platform**: Test on both macOS and Windows
5. **Permission Test**: Run without admin rights on Windows

### Automated Tests

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.diagnostics.wifi import EnableWifi

@pytest.mark.asyncio
async def test_enable_wifi_success():
    """Test successful WiFi enable."""
    diag = EnableWifi()
    
    with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
        # First call: check status (Off)
        # Second call: enable command
        # Third call: verify status (On)
        mock_run.side_effect = [
            AsyncMock(success=True, stdout="Wi-Fi Power (en0): Off", stderr=""),
            AsyncMock(success=True, stdout="", stderr=""),
            AsyncMock(success=True, stdout="Wi-Fi Power (en0): On", stderr=""),
        ]
        
        result = await diag.run()
        
        assert result.success
        assert result.data["changed"] == True
        assert result.data["current_state"] == "on"

@pytest.mark.asyncio
async def test_enable_wifi_already_on():
    """Test when WiFi is already enabled."""
    diag = EnableWifi()
    
    with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.return_value = AsyncMock(
            success=True, 
            stdout="Wi-Fi Power (en0): On",
            stderr=""
        )
        
        result = await diag.run()
        
        assert result.success
        assert result.data["changed"] == False
        assert result.data["previous_state"] == "on"
```

## Implementation Notes

- On macOS, `networksetup` commands typically don't require sudo for enabling WiFi
- On Windows, `netsh` enable commands require Administrator privileges
- After enabling WiFi, the adapter still needs to connect to a network (this tool doesn't handle that)
- Consider adding a `disable_wifi` companion function for completeness
- The tool verifies the state change after enabling to catch hardware switch issues

## Related Functions

- `check_adapter_status`: Run first to diagnose WiFi state, run after to verify connection
- `get_ip_config`: Run after WiFi is enabled and connected to check IP assignment
- `connect_wifi`: Future function to connect to a specific WiFi network

