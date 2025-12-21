# Function: check_adapter_status

## Purpose

Check if network adapters are enabled and operational, identifying which interfaces are up/down and their connection status.

## OSI Layer

**Layer 1 (Physical) / Layer 2 (Data Link)** - Verifies the network interface hardware and link state.

## When to Use

- First diagnostic step when user reports "no internet"
- When troubleshooting connectivity issues
- To identify which network interfaces are available
- To check if WiFi or Ethernet is connected

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| interface_name | string | No | None | Specific interface to check (e.g., "en0", "Ethernet"). If not provided, checks all interfaces. |

## Output Schema

```python
from pydantic import BaseModel, Field
from typing import Literal

class AdapterInfo(BaseModel):
    """Information about a single network adapter."""
    
    name: str = Field(description="Interface name (e.g., en0, Ethernet)")
    display_name: str = Field(description="Human-friendly name if available")
    status: Literal["up", "down", "unknown"] = Field(description="Interface status")
    type: Literal["ethernet", "wifi", "loopback", "virtual", "other"] = Field(
        description="Type of network interface"
    )
    mac_address: str | None = Field(description="MAC/Hardware address")
    has_ip: bool = Field(description="Whether interface has an IP assigned")
    is_connected: bool = Field(description="Whether media/link is connected")


class CheckAdapterStatusResult(BaseModel):
    """Result data for check_adapter_status."""
    
    adapters: list[AdapterInfo] = Field(description="List of network adapters found")
    active_count: int = Field(description="Number of active (up) adapters")
    connected_count: int = Field(description="Number of connected adapters")
    primary_interface: str | None = Field(description="Primary/default interface name")
```

## Platform Commands

### macOS

```bash
# List all network interfaces with status
ifconfig -a

# Get more detailed info about services (optional)
networksetup -listallhardwareports
```

**Parsing Logic:**

1. Parse `ifconfig -a` output by interface blocks (separated by interface name pattern `^\w+:`)
2. For each interface:
   - Extract name from header line (e.g., `en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST>`)
   - Check for `UP` in flags to determine status
   - Check for `RUNNING` flag for connectivity
   - Extract `ether` line for MAC address
   - Check for `inet` line to determine if IP is assigned
3. Identify interface type:
   - `lo0` = loopback
   - `en0`, `en1` = ethernet or wifi (check with `networksetup`)
   - `bridge`, `utun`, `awdl` = virtual

**Example ifconfig output:**
```
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
	options=6463<RXCSUM,TXCSUM,TSO4,TSO6,CHANNEL_IO,PARTIAL_CSUM,ZEROINVERT_CSUM>
	ether a4:83:e7:xx:xx:xx
	inet6 fe80::xxx:xxxx:xxxx:xxxx%en0 prefixlen 64 secured scopeid 0xc
	inet 192.168.1.100 netmask 0xffffff00 broadcast 192.168.1.255
	nd6 options=201<PERFORMNUD,DAD>
	media: autoselect
	status: active
```

### Windows

```powershell
# Get network adapter information
Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, MacAddress, MediaConnectionState, InterfaceType | ConvertTo-Json

# Alternative: Get more details including IP
Get-NetIPInterface | Select-Object InterfaceAlias, InterfaceIndex, ConnectionState, AddressFamily | ConvertTo-Json
```

**Parsing Logic:**

1. Parse JSON output from PowerShell
2. Map fields:
   - `Name` → adapter name
   - `InterfaceDescription` → display name
   - `Status` → "Up" or "Disabled"
   - `MacAddress` → MAC address
   - `MediaConnectionState` → 1=Connected, 0=Disconnected
   - `InterfaceType` → 6=Ethernet, 71=WiFi, 24=Loopback

**Example PowerShell output:**
```json
[
  {
    "Name": "Ethernet",
    "InterfaceDescription": "Intel(R) Ethernet Connection",
    "Status": "Up",
    "MacAddress": "A4-83-E7-XX-XX-XX",
    "MediaConnectionState": 1,
    "InterfaceType": 6
  },
  {
    "Name": "Wi-Fi",
    "InterfaceDescription": "Intel(R) Wi-Fi 6 AX201",
    "Status": "Up",
    "MacAddress": "B4-12-34-XX-XX-XX",
    "MediaConnectionState": 1,
    "InterfaceType": 71
  }
]
```

## Error Handling

| Error Condition | Detection | Suggested Action |
|-----------------|-----------|------------------|
| No adapters found | Empty adapter list | Check if network hardware is installed |
| Command timeout | Timeout exception | System may be unresponsive, try restarting |
| Permission denied | Error in stderr | Run with elevated privileges |
| All adapters down | active_count = 0 | Enable network adapter in system settings |
| No connected adapters | connected_count = 0 | Check physical cable or WiFi connection |

## Example Output

### Success Case (Healthy Network)

```json
{
    "success": true,
    "function_name": "check_adapter_status",
    "platform": "macos",
    "data": {
        "adapters": [
            {
                "name": "en0",
                "display_name": "Wi-Fi",
                "status": "up",
                "type": "wifi",
                "mac_address": "a4:83:e7:xx:xx:xx",
                "has_ip": true,
                "is_connected": true
            },
            {
                "name": "lo0",
                "display_name": "Loopback",
                "status": "up",
                "type": "loopback",
                "mac_address": null,
                "has_ip": true,
                "is_connected": true
            }
        ],
        "active_count": 2,
        "connected_count": 2,
        "primary_interface": "en0"
    },
    "raw_output": "en0: flags=8863<UP,BROADCAST,SMART,RUNNING...",
    "error": null,
    "suggestions": []
}
```

### Failure Case (No Connection)

```json
{
    "success": true,
    "function_name": "check_adapter_status",
    "platform": "macos",
    "data": {
        "adapters": [
            {
                "name": "en0",
                "display_name": "Wi-Fi",
                "status": "up",
                "type": "wifi",
                "mac_address": "a4:83:e7:xx:xx:xx",
                "has_ip": false,
                "is_connected": false
            }
        ],
        "active_count": 1,
        "connected_count": 0,
        "primary_interface": null
    },
    "raw_output": "en0: flags=8863<UP,BROADCAST...",
    "error": null,
    "suggestions": [
        "No adapters are connected to a network",
        "Check if WiFi is connected to an access point",
        "Check if Ethernet cable is plugged in",
        "Run get_ip_config to check DHCP status"
    ]
}
```

### Failure Case (Adapter Disabled)

```json
{
    "success": true,
    "function_name": "check_adapter_status",
    "platform": "windows",
    "data": {
        "adapters": [
            {
                "name": "Ethernet",
                "display_name": "Intel(R) Ethernet Connection",
                "status": "down",
                "type": "ethernet",
                "mac_address": "A4-83-E7-XX-XX-XX",
                "has_ip": false,
                "is_connected": false
            }
        ],
        "active_count": 0,
        "connected_count": 0,
        "primary_interface": null
    },
    "raw_output": "[{\"Name\":\"Ethernet\",\"Status\":\"Disabled\"...}]",
    "error": null,
    "suggestions": [
        "All network adapters are disabled",
        "Enable the network adapter in Network Connections settings",
        "On Windows: Control Panel > Network and Sharing Center > Change adapter settings"
    ]
}
```

## Test Cases

### Manual Testing

1. **Happy Path**: Run on system with active WiFi/Ethernet, verify adapters listed correctly
2. **Disconnected Cable**: Unplug Ethernet, verify `is_connected: false`
3. **Disabled Adapter**: Disable adapter in settings, verify `status: down`
4. **Multiple Adapters**: Test on system with both Ethernet and WiFi
5. **Cross-Platform**: Run on both macOS and Windows, verify consistent schema

### Automated Tests

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.diagnostics.adapter import CheckAdapterStatus

@pytest.mark.asyncio
async def test_check_adapter_status_success():
    """Test successful adapter detection."""
    diag = CheckAdapterStatus()
    
    # Mock ifconfig output
    mock_output = """
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
    ether a4:83:e7:12:34:56
    inet 192.168.1.100 netmask 0xffffff00 broadcast 192.168.1.255
    status: active
"""
    with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.return_value.stdout = mock_output
        mock_run.return_value.success = True
        
        result = await diag.run()
        
        assert result.success
        assert len(result.data["adapters"]) >= 1
        assert result.data["active_count"] >= 1

@pytest.mark.asyncio
async def test_check_adapter_status_no_adapters():
    """Test handling of no adapters found."""
    diag = CheckAdapterStatus()
    
    with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.return_value.stdout = ""
        mock_run.return_value.success = True
        
        result = await diag.run()
        
        assert result.success  # Function succeeded even if no adapters
        assert len(result.data["adapters"]) == 0
        assert len(result.suggestions) > 0
```

## Implementation Notes

- Skip virtual/tunnel interfaces (utun, bridge, awdl) in default output to reduce noise
- Cache the `networksetup -listallhardwareports` output to map interface names to friendly names on macOS
- On Windows, the `Get-NetAdapter` cmdlet requires at least Windows 8/Server 2012
- Consider adding a `verbose` parameter to include all interfaces including virtual ones

## Related Functions

- `get_ip_config`: Run after confirming adapter is up to check IP assignment
- `check_wifi_signal`: Run if WiFi adapter is connected but having issues
- `ping_gateway`: Run after confirming adapter has IP to test gateway connectivity

