# Function: ping_gateway

## Purpose

Test connectivity to the default gateway (router) using ICMP ping. This verifies that the local network path is working correctly before testing external connectivity.

## OSI Layer

**Layer 3 (Network)** - Tests IP-level reachability to the gateway router.

## When to Use

- After confirming valid IP configuration with `get_ip_config`
- When user can't reach the internet but has a valid IP
- To isolate whether the problem is local network or WAN
- First step in the "ping ladder" diagnostic sequence

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| gateway | string | No | None | Gateway IP to ping. If not provided, auto-detects from routing table. |
| count | number | No | 4 | Number of ping packets to send |
| timeout | number | No | 5 | Timeout in seconds per ping |

## Output Schema

```python
from pydantic import BaseModel, Field

class PingResult(BaseModel):
    """Result of a single ping attempt."""
    
    sequence: int = Field(description="Ping sequence number")
    success: bool = Field(description="Whether this ping succeeded")
    time_ms: float | None = Field(description="Round-trip time in milliseconds")
    ttl: int | None = Field(description="Time-to-live of response")


class PingGatewayResult(BaseModel):
    """Result data for ping_gateway."""
    
    gateway_ip: str = Field(description="Gateway IP address that was pinged")
    reachable: bool = Field(description="Whether gateway responded to at least one ping")
    packets_sent: int = Field(description="Number of packets sent")
    packets_received: int = Field(description="Number of packets received")
    packet_loss_percent: float = Field(description="Percentage of packets lost")
    min_time_ms: float | None = Field(description="Minimum round-trip time")
    avg_time_ms: float | None = Field(description="Average round-trip time")
    max_time_ms: float | None = Field(description="Maximum round-trip time")
    results: list[PingResult] = Field(description="Individual ping results")
```

## Platform Commands

### macOS

```bash
# Ping gateway with count and timeout
ping -c 4 -W 5000 192.168.1.1

# Get default gateway (if not provided)
route -n get default | grep gateway
```

**Parsing Logic:**

1. Get gateway from route table if not provided:
   - Parse `route -n get default` output
   - Extract `gateway: 192.168.1.1` line

2. Parse ping output:
   - Individual results: `64 bytes from 192.168.1.1: icmp_seq=0 ttl=64 time=1.234 ms`
   - Summary: `4 packets transmitted, 4 packets received, 0.0% packet loss`
   - Statistics: `round-trip min/avg/max/stddev = 1.123/1.456/2.345/0.234 ms`

**Example ping output:**
```
PING 192.168.1.1 (192.168.1.1): 56 data bytes
64 bytes from 192.168.1.1: icmp_seq=0 ttl=64 time=1.234 ms
64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=1.456 ms
64 bytes from 192.168.1.1: icmp_seq=2 ttl=64 time=1.789 ms
64 bytes from 192.168.1.1: icmp_seq=3 ttl=64 time=1.123 ms

--- 192.168.1.1 ping statistics ---
4 packets transmitted, 4 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 1.123/1.400/1.789/0.245 ms
```

### Windows

```powershell
# Ping gateway with count and timeout
ping -n 4 -w 5000 192.168.1.1

# Get default gateway (if not provided)
(Get-NetRoute -DestinationPrefix '0.0.0.0/0').NextHop
```

**Parsing Logic:**

1. Get gateway from routing table if not provided:
   - Use PowerShell cmdlet to get default route

2. Parse ping output:
   - Individual results: `Reply from 192.168.1.1: bytes=32 time=1ms TTL=64`
   - Summary: `Packets: Sent = 4, Received = 4, Lost = 0 (0% loss)`

**Example ping output:**
```
Pinging 192.168.1.1 with 32 bytes of data:
Reply from 192.168.1.1: bytes=32 time=1ms TTL=64
Reply from 192.168.1.1: bytes=32 time<1ms TTL=64
Reply from 192.168.1.1: bytes=32 time=1ms TTL=64
Reply from 192.168.1.1: bytes=32 time=1ms TTL=64

Ping statistics for 192.168.1.1:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 0ms, Maximum = 1ms, Average = 0ms
```

## Error Handling

| Error Condition | Detection | Suggested Action |
|-----------------|-----------|------------------|
| No gateway found | Cannot determine gateway IP | Run get_ip_config first, check DHCP |
| Request timeout | 100% packet loss | Check cable/WiFi, router may be down |
| Partial loss | 1-99% packet loss | Network congestion or intermittent issue |
| Host unreachable | ICMP unreachable message | Gateway IP may be wrong, check config |
| Network unreachable | ICMP network unreachable | No route to gateway, check IP config |

## Example Output

### Success Case (Gateway Reachable)

```json
{
    "success": true,
    "function_name": "ping_gateway",
    "platform": "macos",
    "data": {
        "gateway_ip": "192.168.1.1",
        "reachable": true,
        "packets_sent": 4,
        "packets_received": 4,
        "packet_loss_percent": 0.0,
        "min_time_ms": 1.123,
        "avg_time_ms": 1.400,
        "max_time_ms": 1.789,
        "results": [
            {"sequence": 0, "success": true, "time_ms": 1.234, "ttl": 64},
            {"sequence": 1, "success": true, "time_ms": 1.456, "ttl": 64},
            {"sequence": 2, "success": true, "time_ms": 1.789, "ttl": 64},
            {"sequence": 3, "success": true, "time_ms": 1.123, "ttl": 64}
        ]
    },
    "raw_output": "PING 192.168.1.1...",
    "error": null,
    "suggestions": []
}
```

### Failure Case (Gateway Unreachable)

```json
{
    "success": true,
    "function_name": "ping_gateway",
    "platform": "macos",
    "data": {
        "gateway_ip": "192.168.1.1",
        "reachable": false,
        "packets_sent": 4,
        "packets_received": 0,
        "packet_loss_percent": 100.0,
        "min_time_ms": null,
        "avg_time_ms": null,
        "max_time_ms": null,
        "results": [
            {"sequence": 0, "success": false, "time_ms": null, "ttl": null},
            {"sequence": 1, "success": false, "time_ms": null, "ttl": null},
            {"sequence": 2, "success": false, "time_ms": null, "ttl": null},
            {"sequence": 3, "success": false, "time_ms": null, "ttl": null}
        ]
    },
    "raw_output": "PING 192.168.1.1...\nRequest timeout...",
    "error": null,
    "suggestions": [
        "Gateway is not responding",
        "Check if router/modem is powered on",
        "Verify Ethernet cable is connected or WiFi is associated",
        "Try restarting the router",
        "Check if gateway IP is correct: 192.168.1.1"
    ]
}
```

### Partial Loss Case

```json
{
    "success": true,
    "function_name": "ping_gateway",
    "platform": "windows",
    "data": {
        "gateway_ip": "192.168.1.1",
        "reachable": true,
        "packets_sent": 4,
        "packets_received": 2,
        "packet_loss_percent": 50.0,
        "min_time_ms": 1.0,
        "avg_time_ms": 1.5,
        "max_time_ms": 2.0,
        "results": [
            {"sequence": 1, "success": true, "time_ms": 1.0, "ttl": 64},
            {"sequence": 2, "success": false, "time_ms": null, "ttl": null},
            {"sequence": 3, "success": true, "time_ms": 2.0, "ttl": 64},
            {"sequence": 4, "success": false, "time_ms": null, "ttl": null}
        ]
    },
    "raw_output": "...",
    "error": null,
    "suggestions": [
        "Intermittent connectivity to gateway (50% packet loss)",
        "This may indicate network congestion or a failing cable/connection",
        "Check WiFi signal strength if on wireless",
        "Try a different Ethernet cable if wired",
        "Consider running check_wifi_signal for more details"
    ]
}
```

## Test Cases

### Manual Testing

1. **Happy Path**: Ping gateway on working network, verify 0% loss
2. **Disconnected**: Unplug cable, verify 100% timeout
3. **Partial Loss**: Stress network while pinging, may see some loss
4. **Wrong Gateway**: Ping non-existent IP, verify error handling
5. **No Gateway**: Remove default route, verify proper error message

### Automated Tests

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.diagnostics.connectivity import PingGateway

@pytest.mark.asyncio
async def test_ping_gateway_success():
    """Test successful gateway ping."""
    diag = PingGateway()
    
    mock_route = "gateway: 192.168.1.1"
    mock_ping = """
PING 192.168.1.1 (192.168.1.1): 56 data bytes
64 bytes from 192.168.1.1: icmp_seq=0 ttl=64 time=1.234 ms
64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=1.456 ms

--- 192.168.1.1 ping statistics ---
2 packets transmitted, 2 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 1.234/1.345/1.456/0.111 ms
"""
    
    with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = [
            AsyncMock(stdout=mock_route, success=True),
            AsyncMock(stdout=mock_ping, success=True),
        ]
        
        result = await diag.run(count=2)
        
        assert result.success
        assert result.data["reachable"]
        assert result.data["packet_loss_percent"] == 0.0

@pytest.mark.asyncio
async def test_ping_gateway_timeout():
    """Test gateway timeout handling."""
    diag = PingGateway()
    
    mock_ping = """
PING 192.168.1.1 (192.168.1.1): 56 data bytes
Request timeout for icmp_seq 0
Request timeout for icmp_seq 1

--- 192.168.1.1 ping statistics ---
2 packets transmitted, 0 packets received, 100.0% packet loss
"""
    
    with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.return_value.stdout = mock_ping
        mock_run.return_value.success = True
        
        result = await diag.run(gateway="192.168.1.1", count=2)
        
        assert result.success  # Function succeeded
        assert not result.data["reachable"]
        assert result.data["packet_loss_percent"] == 100.0
        assert len(result.suggestions) > 0
```

## Implementation Notes

- Ping requires ICMP which may need elevated privileges on some systems
- Some routers block ICMP - document this as a possible false negative
- Windows ping uses `-n` for count, macOS uses `-c`
- Windows timeout is in ms, macOS `-W` is in ms (not seconds despite docs)
- Consider using `subprocess.PIPE` for real-time output in CLI mode
- Gateway detection should be cached from `get_ip_config` when available

## Related Functions

- `get_ip_config`: Run first to ensure valid IP and discover gateway
- `ping_dns`: Run next if gateway succeeds to test WAN connectivity
- `check_adapter_status`: Run if gateway ping fails immediately (no adapter)

