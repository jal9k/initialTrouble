# Function: test_vpn_connectivity

## Purpose

Check VPN connection status and test connectivity through the VPN tunnel. Detects common VPN configurations and verifies the tunnel is passing traffic correctly.

## OSI Layer

**Network Layer (Layer 3)** - Tests VPN tunnel connectivity and routing.

## When to Use

- User reports VPN is connected but can't access internal resources
- Verifying VPN is properly connected
- Diagnosing split tunneling issues
- Checking for DNS leaks
- User says: "VPN connected but not working", "can't access internal site", "VPN keeps disconnecting"

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| vpn_type | string | No | auto-detect | Type of VPN. Options: "wireguard", "openvpn", "ipsec", "cisco", "globalprotect" |
| test_endpoint | string | No | None | Internal endpoint to test through VPN (e.g., "192.168.10.1", "intranet.company.com") |

## Output Schema

```python
class TestVPNConnectivityResult(BaseModel):
    """Result data specific to test_vpn_connectivity."""
    
    vpn_connected: bool = Field(description="Whether VPN is active")
    vpn_type: str | None = Field(description="Detected or specified VPN type")
    vpn_interface: str | None = Field(description="Interface name (e.g., utun3, wg0)")
    vpn_ip: str | None = Field(description="IP address assigned by VPN")
    routes_active: bool = Field(description="Whether VPN routes are present")
    dns_via_vpn: bool = Field(description="Whether DNS goes through VPN")
    internal_reachable: bool | None = Field(description="Whether test_endpoint was reachable")
    detection_method: str = Field(description="How VPN was detected")
```

## Platform-Specific Detection

### macOS

**Interface Detection:**
```bash
# List all interfaces
ifconfig -l

# Check for VPN interfaces (utun*, ipsec*, ppp*)
ifconfig utun0

# Check scutil for system VPN connections
scutil --nc list
```

**VPN Interface Patterns:**
- `utun*` - WireGuard, OpenVPN, various apps
- `ipsec*` - IPSec VPNs
- `ppp*` - L2TP/PPTP

**DNS Check:**
```bash
scutil --dns
```

### Windows

**VPN Detection:**
```powershell
# Check Windows built-in VPN
Get-VpnConnection | Where-Object {$_.ConnectionStatus -eq 'Connected'}

# Check for VPN network adapters
Get-NetAdapter | Where-Object {$_.InterfaceDescription -match 'VPN|TAP|WireGuard'}
```

**VPN Interface Patterns:**
- "WireGuard Tunnel" - WireGuard
- "TAP-Windows Adapter" - OpenVPN
- Cisco, GlobalProtect, etc. in description

**DNS Check:**
```powershell
Get-DnsClientServerAddress
```

### Linux

**Interface Detection:**
```bash
# WireGuard interfaces
ip link show type wireguard

# All tun/tap interfaces
ip link show | grep -E 'tun|tap|wg'

# NetworkManager VPNs
nmcli connection show --active | grep vpn
```

**VPN Interface Patterns:**
- `wg*` - WireGuard
- `tun*` - OpenVPN (routed)
- `tap*` - OpenVPN (bridged)
- `ppp*` - L2TP/PPTP

**DNS Check:**
```bash
cat /etc/resolv.conf
resolvectl status
```

## Tests Performed

1. **VPN interface exists and is up** - Check for active VPN interfaces
2. **VPN interface has IP assigned** - Verify the tunnel has an IP
3. **Routing table includes VPN routes** - Check for VPN routing entries
4. **DNS configured to use VPN** - Check for private DNS servers
5. **Internal endpoint reachable** - Ping test if endpoint provided

## Error Handling

| Error Condition | Detection | Suggested Action |
|-----------------|-----------|------------------|
| No VPN detected | No VPN interfaces found | Connect to VPN and retry |
| VPN connected, no IP | Interface up but no inet | Check VPN authentication |
| No VPN routes | Routing table missing VPN entries | Check VPN client settings |
| DNS leak | Public DNS servers used | Enable VPN DNS in client settings |
| Internal unreachable | Ping fails to test_endpoint | Check VPN routing, verify endpoint is up |

## Example Output

### VPN Connected Successfully

```json
{
    "success": true,
    "function_name": "test_vpn_connectivity",
    "platform": "macos",
    "data": {
        "vpn_connected": true,
        "vpn_type": "wireguard",
        "vpn_interface": "utun3",
        "vpn_ip": "10.8.0.15",
        "routes_active": true,
        "dns_via_vpn": true,
        "internal_reachable": true,
        "detection_method": "interface_scan"
    },
    "raw_output": "",
    "error": null,
    "suggestions": [
        "VPN connected with IP: 10.8.0.15",
        "Successfully reached internal endpoint: 192.168.10.1"
    ]
}
```

### VPN Not Connected

```json
{
    "success": true,
    "function_name": "test_vpn_connectivity",
    "platform": "windows",
    "data": {
        "vpn_connected": false,
        "vpn_type": null,
        "vpn_interface": null,
        "vpn_ip": null,
        "routes_active": false,
        "dns_via_vpn": false,
        "internal_reachable": null,
        "detection_method": "Get-VpnConnection"
    },
    "raw_output": "",
    "error": null,
    "suggestions": [
        "No active VPN connection detected",
        "Connect to your VPN and try again",
        "Check VPN client application is running"
    ]
}
```

### VPN Connected but Issues Detected

```json
{
    "success": true,
    "function_name": "test_vpn_connectivity",
    "platform": "linux",
    "data": {
        "vpn_connected": true,
        "vpn_type": "openvpn",
        "vpn_interface": "tun0",
        "vpn_ip": "10.8.0.42",
        "routes_active": false,
        "dns_via_vpn": false,
        "internal_reachable": false,
        "detection_method": "ip_link"
    },
    "raw_output": "",
    "error": null,
    "suggestions": [
        "VPN connected with IP: 10.8.0.42",
        "VPN routes may not be configured. Check VPN client settings.",
        "DNS does not appear to go through VPN. This may cause DNS leaks.",
        "Cannot reach internal endpoint 192.168.10.1. Check VPN routing."
    ]
}
```

## Test Cases

### Manual Testing

1. **No VPN**: Run without any VPN connected, verify "not connected" result
2. **WireGuard**: Connect WireGuard, verify detection and IP
3. **OpenVPN**: Connect OpenVPN, verify detection and IP
4. **Internal Endpoint**: Provide internal IP, verify ping test
5. **DNS Leak Check**: Verify DNS through VPN is detected correctly
6. **Cross-Platform**: Test on macOS, Windows, and Linux

### Automated Tests

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.diagnostics.vpn import TestVPNConnectivity

@pytest.mark.asyncio
async def test_vpn_not_connected():
    """Test detection of no VPN connection."""
    diag = TestVPNConnectivity()
    
    with patch.object(diag, '_detect_vpn', new_callable=AsyncMock) as mock_detect:
        mock_detect.return_value = {"connected": False, "method": "test"}
        
        result = await diag.run()
        
        assert result.success
        assert result.data["vpn_connected"] == False

@pytest.mark.asyncio
async def test_vpn_connected():
    """Test detection of connected VPN."""
    diag = TestVPNConnectivity()
    
    with patch.object(diag, '_detect_vpn', new_callable=AsyncMock) as mock_detect:
        with patch.object(diag, '_get_vpn_ip', new_callable=AsyncMock) as mock_ip:
            with patch.object(diag, '_check_vpn_routes', new_callable=AsyncMock) as mock_routes:
                with patch.object(diag, '_check_dns_via_vpn', new_callable=AsyncMock) as mock_dns:
                    mock_detect.return_value = {
                        "connected": True,
                        "interface": "utun3",
                        "type": "wireguard",
                        "method": "interface_scan"
                    }
                    mock_ip.return_value = "10.8.0.15"
                    mock_routes.return_value = True
                    mock_dns.return_value = True
                    
                    result = await diag.run()
                    
                    assert result.success
                    assert result.data["vpn_connected"] == True
                    assert result.data["vpn_ip"] == "10.8.0.15"

@pytest.mark.asyncio
async def test_vpn_internal_endpoint():
    """Test internal endpoint connectivity check."""
    diag = TestVPNConnectivity()
    
    with patch.object(diag, '_detect_vpn', new_callable=AsyncMock) as mock_detect:
        with patch.object(diag, '_get_vpn_ip', new_callable=AsyncMock) as mock_ip:
            with patch.object(diag, '_check_vpn_routes', new_callable=AsyncMock) as mock_routes:
                with patch.object(diag, '_check_dns_via_vpn', new_callable=AsyncMock) as mock_dns:
                    with patch.object(diag, '_test_endpoint', new_callable=AsyncMock) as mock_endpoint:
                        mock_detect.return_value = {"connected": True, "interface": "wg0", "type": "wireguard", "method": "test"}
                        mock_ip.return_value = "10.8.0.15"
                        mock_routes.return_value = True
                        mock_dns.return_value = True
                        mock_endpoint.return_value = True
                        
                        result = await diag.run(test_endpoint="192.168.10.1")
                        
                        assert result.success
                        assert result.data["internal_reachable"] == True
```

## Implementation Notes

- Auto-detects VPN type from interface names and descriptions
- Supports multiple detection methods per platform for reliability
- Checks both interface status and routing table for comprehensive analysis
- DNS leak detection looks for private IP ranges in DNS configuration
- Uses platform-specific commands but provides unified result format

## Related Functions

- `check_adapter_status`: Should be run first to verify network is working
- `get_ip_config`: Provides broader network configuration context
- `ping_dns`: Verifies general internet connectivity
- `test_dns_resolution`: Can be used to check DNS resolution through VPN

