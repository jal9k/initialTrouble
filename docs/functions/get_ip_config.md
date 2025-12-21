# Function: get_ip_config

## Purpose

Retrieve IP configuration for network interfaces including IP address, subnet mask, gateway, and DHCP status. Identifies common IP issues like APIPA addresses (169.254.x.x) indicating DHCP failure.

## OSI Layer

**Layer 3 (Network)** - Verifies IP addressing and routing configuration.

## When to Use

- After confirming adapters are up with `check_adapter_status`
- When user has connectivity but can't reach internet
- To check if DHCP is working properly
- To identify gateway address for connectivity testing
- When troubleshooting "Limited Connectivity" issues

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| interface_name | string | No | None | Specific interface to check. If not provided, checks all active interfaces. |

## Output Schema

```python
from pydantic import BaseModel, Field
from typing import Literal

class IPConfig(BaseModel):
    """IP configuration for a network interface."""
    
    interface: str = Field(description="Interface name (e.g., en0, Ethernet)")
    ip_address: str | None = Field(description="IPv4 address")
    subnet_mask: str | None = Field(description="Subnet mask")
    gateway: str | None = Field(description="Default gateway IP")
    dns_servers: list[str] = Field(description="Configured DNS servers")
    dhcp_enabled: bool = Field(description="Whether DHCP is enabled")
    dhcp_server: str | None = Field(description="DHCP server address if known")
    lease_obtained: str | None = Field(description="When DHCP lease was obtained")
    lease_expires: str | None = Field(description="When DHCP lease expires")
    is_apipa: bool = Field(description="True if using APIPA/link-local address (169.254.x.x)")
    ipv6_address: str | None = Field(description="IPv6 address if available")


class GetIPConfigResult(BaseModel):
    """Result data for get_ip_config."""
    
    interfaces: list[IPConfig] = Field(description="IP configuration for each interface")
    has_valid_ip: bool = Field(description="At least one interface has valid IP")
    has_gateway: bool = Field(description="At least one interface has gateway configured")
    primary_ip: str | None = Field(description="Primary/default IP address")
    primary_gateway: str | None = Field(description="Primary/default gateway")
```

## Platform Commands

### macOS

```bash
# Get IP configuration for all interfaces
ifconfig

# Get routing table for gateway info
netstat -nr | grep default

# Get DNS configuration
scutil --dns | grep "nameserver"

# Alternative for detailed DHCP info
ipconfig getpacket en0
```

**Parsing Logic:**

1. Parse `ifconfig` for each interface:
   - Extract `inet` line for IPv4: `inet 192.168.1.100 netmask 0xffffff00`
   - Convert hex netmask to dotted notation (0xffffff00 → 255.255.255.0)
   - Extract `inet6` for IPv6 address
   - Check if IP starts with 169.254 for APIPA detection

2. Parse `netstat -nr` for default gateway:
   - Look for `default` entry
   - Extract gateway IP and associated interface

3. Parse `scutil --dns` for DNS servers:
   - Extract `nameserver[n]` entries

**Example ifconfig output:**
```
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
    inet 192.168.1.100 netmask 0xffffff00 broadcast 192.168.1.255
    inet6 fe80::xxx:xxxx:xxxx:xxxx%en0 prefixlen 64
```

**Example netstat -nr output:**
```
Routing tables
Internet:
Destination        Gateway            Flags    Netif
default            192.168.1.1        UGScg    en0
```

### Windows

```powershell
# Get comprehensive IP configuration
Get-NetIPConfiguration | ConvertTo-Json -Depth 4

# Alternative: traditional ipconfig output
ipconfig /all
```

**Parsing Logic:**

1. Parse JSON from `Get-NetIPConfiguration`:
   - `InterfaceAlias` → interface name
   - `IPv4Address.IPAddress` → IP address
   - `IPv4DefaultGateway.NextHop` → gateway
   - `DNSServer.ServerAddresses` → DNS servers

2. For DHCP info, parse `ipconfig /all`:
   - Look for "DHCP Enabled" line
   - Extract "DHCP Server" line
   - Extract "Lease Obtained" and "Lease Expires"

**Example PowerShell output:**
```json
{
    "InterfaceAlias": "Ethernet",
    "InterfaceIndex": 5,
    "IPv4Address": {
        "IPAddress": "192.168.1.100",
        "PrefixLength": 24
    },
    "IPv4DefaultGateway": {
        "NextHop": "192.168.1.1"
    },
    "DNSServer": [
        {"ServerAddresses": ["8.8.8.8", "8.8.4.4"]}
    ]
}
```

## Error Handling

| Error Condition | Detection | Suggested Action |
|-----------------|-----------|------------------|
| No IP assigned | ip_address is None | Check if adapter is connected, verify DHCP server |
| APIPA address | is_apipa = True | DHCP server unreachable, check network cable/WiFi, verify DHCP server is running |
| No gateway | gateway is None | Check DHCP configuration or set static gateway |
| Multiple gateways | More than one default route | May cause routing issues, verify network config |
| No DNS servers | dns_servers empty | Set DNS manually or check DHCP |

## Example Output

### Success Case (Healthy Configuration)

```json
{
    "success": true,
    "function_name": "get_ip_config",
    "platform": "macos",
    "data": {
        "interfaces": [
            {
                "interface": "en0",
                "ip_address": "192.168.1.100",
                "subnet_mask": "255.255.255.0",
                "gateway": "192.168.1.1",
                "dns_servers": ["8.8.8.8", "8.8.4.4"],
                "dhcp_enabled": true,
                "dhcp_server": "192.168.1.1",
                "lease_obtained": "2024-01-15 10:30:00",
                "lease_expires": "2024-01-16 10:30:00",
                "is_apipa": false,
                "ipv6_address": "fe80::1234:5678:abcd:ef00"
            }
        ],
        "has_valid_ip": true,
        "has_gateway": true,
        "primary_ip": "192.168.1.100",
        "primary_gateway": "192.168.1.1"
    },
    "raw_output": "...",
    "error": null,
    "suggestions": []
}
```

### Failure Case (DHCP Failure - APIPA)

```json
{
    "success": true,
    "function_name": "get_ip_config",
    "platform": "windows",
    "data": {
        "interfaces": [
            {
                "interface": "Ethernet",
                "ip_address": "169.254.45.123",
                "subnet_mask": "255.255.0.0",
                "gateway": null,
                "dns_servers": [],
                "dhcp_enabled": true,
                "dhcp_server": null,
                "lease_obtained": null,
                "lease_expires": null,
                "is_apipa": true,
                "ipv6_address": null
            }
        ],
        "has_valid_ip": false,
        "has_gateway": false,
        "primary_ip": "169.254.45.123",
        "primary_gateway": null
    },
    "raw_output": "...",
    "error": null,
    "suggestions": [
        "APIPA address detected (169.254.x.x) - DHCP server is unreachable",
        "Check physical network connection",
        "Verify DHCP server is running on the network",
        "Try releasing and renewing IP: ipconfig /release && ipconfig /renew",
        "If on WiFi, try reconnecting to the network"
    ]
}
```

### Failure Case (No IP Address)

```json
{
    "success": true,
    "function_name": "get_ip_config",
    "platform": "macos",
    "data": {
        "interfaces": [
            {
                "interface": "en0",
                "ip_address": null,
                "subnet_mask": null,
                "gateway": null,
                "dns_servers": [],
                "dhcp_enabled": true,
                "dhcp_server": null,
                "lease_obtained": null,
                "lease_expires": null,
                "is_apipa": false,
                "ipv6_address": null
            }
        ],
        "has_valid_ip": false,
        "has_gateway": false,
        "primary_ip": null,
        "primary_gateway": null
    },
    "raw_output": "...",
    "error": null,
    "suggestions": [
        "No IP address assigned to interface",
        "Run check_adapter_status to verify adapter is connected",
        "Check if DHCP server is available on the network",
        "Try: sudo ipconfig set en0 DHCP"
    ]
}
```

## Test Cases

### Manual Testing

1. **Happy Path**: Run on system with valid DHCP lease
2. **APIPA Detection**: Disconnect from network, wait for APIPA, verify detection
3. **Static IP**: Configure static IP, verify DHCP shows as disabled
4. **Multiple Interfaces**: Test with both Ethernet and WiFi active
5. **IPv6 Only**: Test on IPv6-only network if available

### Automated Tests

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.diagnostics.ip_config import GetIPConfig

@pytest.mark.asyncio
async def test_get_ip_config_success():
    """Test successful IP configuration retrieval."""
    diag = GetIPConfig()
    
    mock_ifconfig = """
en0: flags=8863<UP,BROADCAST,SMART,RUNNING>
    inet 192.168.1.100 netmask 0xffffff00 broadcast 192.168.1.255
"""
    mock_netstat = """
default            192.168.1.1        UGScg    en0
"""
    
    with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = [
            AsyncMock(stdout=mock_ifconfig, success=True),
            AsyncMock(stdout=mock_netstat, success=True),
        ]
        
        result = await diag.run()
        
        assert result.success
        assert result.data["has_valid_ip"]
        assert result.data["primary_gateway"] == "192.168.1.1"

@pytest.mark.asyncio
async def test_get_ip_config_apipa_detection():
    """Test APIPA address detection."""
    diag = GetIPConfig()
    
    mock_ifconfig = """
en0: flags=8863<UP,BROADCAST,SMART,RUNNING>
    inet 169.254.45.123 netmask 0xffff0000
"""
    
    with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.return_value.stdout = mock_ifconfig
        mock_run.return_value.success = True
        
        result = await diag.run()
        
        assert result.success
        assert result.data["interfaces"][0]["is_apipa"]
        assert not result.data["has_valid_ip"]
        assert len(result.suggestions) > 0
```

## Implementation Notes

- Hex netmask conversion: `0xffffff00` → split into bytes, convert each to decimal
- APIPA range: 169.254.0.0/16 (169.254.0.0 - 169.254.255.255)
- On macOS, `ipconfig getpacket en0` provides DHCP details but may fail if not using DHCP
- Consider caching gateway info as it's used by subsequent `ping_gateway` diagnostic
- Private IP ranges for reference: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16

## Related Functions

- `check_adapter_status`: Should run first to verify adapters are up
- `ping_gateway`: Run next to verify gateway is reachable
- `ping_dns`: Run to verify external connectivity
- `test_dns_resolution`: Final check for full connectivity

