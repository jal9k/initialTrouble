# Function: ping_dns

## Purpose

Test connectivity to external DNS servers (like 8.8.8.8 or 1.1.1.1) using ICMP ping. This verifies that the internet connection is working at the network layer, independent of DNS resolution.

## OSI Layer

**Layer 3 (Network)** - Tests IP-level reachability to external hosts through the WAN connection.

## When to Use

- After `ping_gateway` succeeds to verify WAN connectivity
- When user can reach local network but not internet
- To isolate DNS resolution issues from connectivity issues
- When websites don't load but you need to verify raw IP connectivity

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| dns_servers | array | No | ["8.8.8.8", "1.1.1.1"] | DNS servers to ping |
| count | number | No | 4 | Number of ping packets per server |
| timeout | number | No | 5 | Timeout in seconds per ping |

## Output Schema

```python
from pydantic import BaseModel, Field

class DNSPingResult(BaseModel):
    """Ping result for a single DNS server."""
    
    server: str = Field(description="DNS server IP address")
    name: str = Field(description="Human-readable name (e.g., 'Google DNS')")
    reachable: bool = Field(description="Whether server responded")
    packets_sent: int = Field(description="Number of packets sent")
    packets_received: int = Field(description="Number of packets received")
    packet_loss_percent: float = Field(description="Percentage of packets lost")
    avg_time_ms: float | None = Field(description="Average round-trip time")


class PingDNSResult(BaseModel):
    """Result data for ping_dns."""
    
    servers_tested: int = Field(description="Number of DNS servers tested")
    servers_reachable: int = Field(description="Number of reachable servers")
    internet_accessible: bool = Field(description="Whether at least one external server is reachable")
    results: list[DNSPingResult] = Field(description="Results for each DNS server")
    best_server: str | None = Field(description="Fastest responding server")
    best_latency_ms: float | None = Field(description="Latency to fastest server")
```

## Platform Commands

### macOS

```bash
# Ping Google DNS
ping -c 4 -W 5000 8.8.8.8

# Ping Cloudflare DNS
ping -c 4 -W 5000 1.1.1.1
```

**Parsing Logic:**

Same as `ping_gateway` - parse individual responses and summary statistics.

**DNS Server Reference:**
| Server | IP | Name |
|--------|-----|------|
| Google | 8.8.8.8 | Google Public DNS |
| Google | 8.8.4.4 | Google Public DNS (secondary) |
| Cloudflare | 1.1.1.1 | Cloudflare DNS |
| Cloudflare | 1.0.0.1 | Cloudflare DNS (secondary) |
| Quad9 | 9.9.9.9 | Quad9 DNS |
| OpenDNS | 208.67.222.222 | OpenDNS |

### Windows

```powershell
# Ping Google DNS
ping -n 4 -w 5000 8.8.8.8

# Ping Cloudflare DNS
ping -n 4 -w 5000 1.1.1.1
```

**Parsing Logic:**

Same as `ping_gateway` for Windows format.

## Error Handling

| Error Condition | Detection | Suggested Action |
|-----------------|-----------|------------------|
| All servers unreachable | internet_accessible = false | WAN connection issue, check ISP |
| High latency (>100ms) | avg_time_ms > 100 | Network congestion, ISP issues |
| Partial reachability | Some servers work, others don't | Possible ISP routing issue |
| Request timeout | 100% loss to specific server | Server may be blocked by firewall |

## Example Output

### Success Case (Internet Accessible)

```json
{
    "success": true,
    "function_name": "ping_dns",
    "platform": "macos",
    "data": {
        "servers_tested": 2,
        "servers_reachable": 2,
        "internet_accessible": true,
        "results": [
            {
                "server": "8.8.8.8",
                "name": "Google Public DNS",
                "reachable": true,
                "packets_sent": 4,
                "packets_received": 4,
                "packet_loss_percent": 0.0,
                "avg_time_ms": 15.234
            },
            {
                "server": "1.1.1.1",
                "name": "Cloudflare DNS",
                "reachable": true,
                "packets_sent": 4,
                "packets_received": 4,
                "packet_loss_percent": 0.0,
                "avg_time_ms": 12.567
            }
        ],
        "best_server": "1.1.1.1",
        "best_latency_ms": 12.567
    },
    "raw_output": "...",
    "error": null,
    "suggestions": []
}
```

### Failure Case (No Internet)

```json
{
    "success": true,
    "function_name": "ping_dns",
    "platform": "windows",
    "data": {
        "servers_tested": 2,
        "servers_reachable": 0,
        "internet_accessible": false,
        "results": [
            {
                "server": "8.8.8.8",
                "name": "Google Public DNS",
                "reachable": false,
                "packets_sent": 4,
                "packets_received": 0,
                "packet_loss_percent": 100.0,
                "avg_time_ms": null
            },
            {
                "server": "1.1.1.1",
                "name": "Cloudflare DNS",
                "reachable": false,
                "packets_sent": 4,
                "packets_received": 0,
                "packet_loss_percent": 100.0,
                "avg_time_ms": null
            }
        ],
        "best_server": null,
        "best_latency_ms": null
    },
    "raw_output": "Request timed out...",
    "error": null,
    "suggestions": [
        "Cannot reach external DNS servers - no internet connectivity",
        "Gateway ping succeeded, so this is a WAN issue",
        "Check if modem is connected to ISP",
        "Contact ISP if modem shows connected but no internet",
        "Check if there's an ISP outage in your area"
    ]
}
```

### Partial Success Case

```json
{
    "success": true,
    "function_name": "ping_dns",
    "platform": "macos",
    "data": {
        "servers_tested": 2,
        "servers_reachable": 1,
        "internet_accessible": true,
        "results": [
            {
                "server": "8.8.8.8",
                "name": "Google Public DNS",
                "reachable": true,
                "packets_sent": 4,
                "packets_received": 4,
                "packet_loss_percent": 0.0,
                "avg_time_ms": 20.5
            },
            {
                "server": "1.1.1.1",
                "name": "Cloudflare DNS",
                "reachable": false,
                "packets_sent": 4,
                "packets_received": 0,
                "packet_loss_percent": 100.0,
                "avg_time_ms": null
            }
        ],
        "best_server": "8.8.8.8",
        "best_latency_ms": 20.5
    },
    "raw_output": "...",
    "error": null,
    "suggestions": [
        "Internet is accessible but some DNS servers are unreachable",
        "This may indicate ISP routing issues to specific servers",
        "Consider using the reachable DNS server (8.8.8.8) for name resolution"
    ]
}
```

## Test Cases

### Manual Testing

1. **Happy Path**: Ping on working connection, verify both servers reachable
2. **No Internet**: Disconnect WAN, verify failure detection
3. **High Latency**: Test on slow connection, verify latency reporting
4. **Firewall Block**: Block ICMP, verify graceful handling

### Automated Tests

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.diagnostics.connectivity import PingDNS

@pytest.mark.asyncio
async def test_ping_dns_success():
    """Test successful DNS server ping."""
    diag = PingDNS()
    
    mock_ping_google = """
PING 8.8.8.8 (8.8.8.8): 56 data bytes
64 bytes from 8.8.8.8: icmp_seq=0 ttl=117 time=15.234 ms

--- 8.8.8.8 ping statistics ---
1 packets transmitted, 1 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 15.234/15.234/15.234/0.000 ms
"""
    
    mock_ping_cf = """
PING 1.1.1.1 (1.1.1.1): 56 data bytes
64 bytes from 1.1.1.1: icmp_seq=0 ttl=57 time=12.567 ms

--- 1.1.1.1 ping statistics ---
1 packets transmitted, 1 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 12.567/12.567/12.567/0.000 ms
"""
    
    with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = [
            AsyncMock(stdout=mock_ping_google, success=True),
            AsyncMock(stdout=mock_ping_cf, success=True),
        ]
        
        result = await diag.run(count=1)
        
        assert result.success
        assert result.data["internet_accessible"]
        assert result.data["servers_reachable"] == 2

@pytest.mark.asyncio
async def test_ping_dns_no_internet():
    """Test handling of no internet connectivity."""
    diag = PingDNS()
    
    mock_timeout = """
PING 8.8.8.8 (8.8.8.8): 56 data bytes
Request timeout for icmp_seq 0

--- 8.8.8.8 ping statistics ---
1 packets transmitted, 0 packets received, 100.0% packet loss
"""
    
    with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.return_value.stdout = mock_timeout
        mock_run.return_value.success = True
        
        result = await diag.run(dns_servers=["8.8.8.8"], count=1)
        
        assert result.success
        assert not result.data["internet_accessible"]
        assert len(result.suggestions) > 0
```

## Implementation Notes

- Test multiple DNS servers in parallel using `asyncio.gather()` for faster results
- Order results by latency to identify best server
- These servers are specifically chosen because they are highly reliable
- ICMP may be blocked by some corporate firewalls - note this in suggestions if all fail
- Consider adding traceroute suggestion if gateway works but DNS servers don't

## Related Functions

- `ping_gateway`: Must succeed before this test is meaningful
- `test_dns_resolution`: Run next to verify DNS resolution is working
- `check_firewall_rules`: Run if ICMP might be blocked

