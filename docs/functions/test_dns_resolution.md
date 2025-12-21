# Function: test_dns_resolution

## Purpose

Test DNS name resolution by resolving common hostnames to IP addresses. This verifies the final step in the diagnostic ladder - that the system can translate domain names to IP addresses.

## OSI Layer

**Layer 7 (Application)** - Tests the DNS protocol which is an application-layer service.

## When to Use

- After `ping_dns` succeeds (raw IP connectivity works)
- When user reports "websites don't load" but ping works
- To verify DNS server configuration
- To diagnose DNS poisoning or hijacking
- Final step in the "ping ladder" diagnostic sequence

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| hostnames | array | No | ["google.com", "cloudflare.com"] | Hostnames to resolve |
| dns_server | string | No | None | Specific DNS server to use. If not provided, uses system default. |
| timeout | number | No | 5 | Timeout in seconds for resolution |

## Output Schema

```python
from pydantic import BaseModel, Field
from typing import Literal

class ResolutionResult(BaseModel):
    """Result of resolving a single hostname."""
    
    hostname: str = Field(description="Hostname that was resolved")
    resolved: bool = Field(description="Whether resolution succeeded")
    ip_addresses: list[str] = Field(description="Resolved IP addresses (may have multiple)")
    resolution_time_ms: float | None = Field(description="Time to resolve in milliseconds")
    dns_server_used: str | None = Field(description="DNS server that answered")
    record_type: Literal["A", "AAAA", "CNAME"] | None = Field(description="Type of record returned")
    error: str | None = Field(description="Error message if failed")


class TestDNSResolutionResult(BaseModel):
    """Result data for test_dns_resolution."""
    
    hosts_tested: int = Field(description="Number of hostnames tested")
    hosts_resolved: int = Field(description="Number successfully resolved")
    dns_working: bool = Field(description="Whether DNS resolution is functional")
    results: list[ResolutionResult] = Field(description="Results for each hostname")
    avg_resolution_time_ms: float | None = Field(description="Average resolution time")
    dns_server: str | None = Field(description="DNS server used for queries")
```

## Platform Commands

### macOS

```bash
# Resolve hostname using system DNS
nslookup google.com

# Resolve using specific DNS server
nslookup google.com 8.8.8.8

# Alternative: dig command (more detailed)
dig google.com +short +time=5

# Alternative: Using host command
host -W 5 google.com
```

**Parsing Logic:**

1. Parse `nslookup` output:
   - Look for "Address:" lines after "Non-authoritative answer:" section
   - Extract server from "Server:" line
   - Handle "** server can't find" for failed lookups

**Example nslookup output (success):**
```
Server:		192.168.1.1
Address:	192.168.1.1#53

Non-authoritative answer:
Name:	google.com
Address: 142.250.80.46
```

**Example nslookup output (failure):**
```
Server:		192.168.1.1
Address:	192.168.1.1#53

** server can't find google.com: NXDOMAIN
```

### Windows

```powershell
# Resolve hostname using system DNS
nslookup google.com

# Resolve using specific DNS server
nslookup google.com 8.8.8.8

# Alternative: Using Resolve-DnsName (PowerShell native)
Resolve-DnsName -Name google.com -Type A | ConvertTo-Json
```

**Parsing Logic:**

1. For `Resolve-DnsName` (preferred):
   - Parse JSON output directly
   - Extract `IPAddress` field

2. For `nslookup`:
   - Similar parsing to macOS
   - Windows format is slightly different but same structure

**Example PowerShell output:**
```json
{
    "Name": "google.com",
    "Type": "A",
    "TTL": 300,
    "IPAddress": "142.250.80.46"
}
```

## Error Handling

| Error Condition | Detection | Suggested Action |
|-----------------|-----------|------------------|
| NXDOMAIN | "can't find" in output | Domain doesn't exist or is blocked |
| SERVFAIL | Server failure message | DNS server issue, try another server |
| Timeout | Command timeout | DNS server not responding |
| No DNS server | Cannot determine DNS server | Check network configuration |
| All lookups fail | dns_working = false | DNS misconfigured or blocked |

## Example Output

### Success Case (DNS Working)

```json
{
    "success": true,
    "function_name": "test_dns_resolution",
    "platform": "macos",
    "data": {
        "hosts_tested": 2,
        "hosts_resolved": 2,
        "dns_working": true,
        "results": [
            {
                "hostname": "google.com",
                "resolved": true,
                "ip_addresses": ["142.250.80.46", "142.250.80.47"],
                "resolution_time_ms": 23.5,
                "dns_server_used": "192.168.1.1",
                "record_type": "A",
                "error": null
            },
            {
                "hostname": "cloudflare.com",
                "resolved": true,
                "ip_addresses": ["104.16.132.229", "104.16.133.229"],
                "resolution_time_ms": 18.2,
                "dns_server_used": "192.168.1.1",
                "record_type": "A",
                "error": null
            }
        ],
        "avg_resolution_time_ms": 20.85,
        "dns_server": "192.168.1.1"
    },
    "raw_output": "Server: 192.168.1.1...",
    "error": null,
    "suggestions": []
}
```

### Failure Case (DNS Not Working)

```json
{
    "success": true,
    "function_name": "test_dns_resolution",
    "platform": "windows",
    "data": {
        "hosts_tested": 2,
        "hosts_resolved": 0,
        "dns_working": false,
        "results": [
            {
                "hostname": "google.com",
                "resolved": false,
                "ip_addresses": [],
                "resolution_time_ms": null,
                "dns_server_used": "192.168.1.1",
                "record_type": null,
                "error": "DNS request timed out"
            },
            {
                "hostname": "cloudflare.com",
                "resolved": false,
                "ip_addresses": [],
                "resolution_time_ms": null,
                "dns_server_used": "192.168.1.1",
                "record_type": null,
                "error": "DNS request timed out"
            }
        ],
        "avg_resolution_time_ms": null,
        "dns_server": "192.168.1.1"
    },
    "raw_output": "DNS request timed out...",
    "error": null,
    "suggestions": [
        "DNS resolution is not working",
        "ping_dns succeeded, so internet is accessible - this is a DNS-specific issue",
        "Try changing DNS server to 8.8.8.8 or 1.1.1.1",
        "On macOS: System Preferences > Network > Advanced > DNS",
        "On Windows: Network adapter settings > IPv4 > DNS server addresses"
    ]
}
```

### Partial Success Case

```json
{
    "success": true,
    "function_name": "test_dns_resolution",
    "platform": "macos",
    "data": {
        "hosts_tested": 2,
        "hosts_resolved": 1,
        "dns_working": true,
        "results": [
            {
                "hostname": "google.com",
                "resolved": true,
                "ip_addresses": ["142.250.80.46"],
                "resolution_time_ms": 25.0,
                "dns_server_used": "192.168.1.1",
                "record_type": "A",
                "error": null
            },
            {
                "hostname": "blocked-site.com",
                "resolved": false,
                "ip_addresses": [],
                "resolution_time_ms": null,
                "dns_server_used": "192.168.1.1",
                "record_type": null,
                "error": "NXDOMAIN - domain not found"
            }
        ],
        "avg_resolution_time_ms": 25.0,
        "dns_server": "192.168.1.1"
    },
    "raw_output": "...",
    "error": null,
    "suggestions": [
        "DNS is working but some domains failed to resolve",
        "blocked-site.com returned NXDOMAIN - domain may not exist or may be blocked",
        "If this domain should exist, the DNS server may be filtering it"
    ]
}
```

## Test Cases

### Manual Testing

1. **Happy Path**: Resolve common domains on working DNS
2. **No DNS**: Point to invalid DNS server, verify failure handling
3. **Blocked Domain**: Try resolving a domain known to be blocked
4. **Slow DNS**: Test with high-latency DNS server
5. **Custom DNS**: Test with specific DNS server parameter

### Automated Tests

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.diagnostics.dns import TestDNSResolution

@pytest.mark.asyncio
async def test_dns_resolution_success():
    """Test successful DNS resolution."""
    diag = TestDNSResolution()
    
    mock_nslookup = """
Server:		192.168.1.1
Address:	192.168.1.1#53

Non-authoritative answer:
Name:	google.com
Address: 142.250.80.46
"""
    
    with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.return_value.stdout = mock_nslookup
        mock_run.return_value.success = True
        
        result = await diag.run(hostnames=["google.com"])
        
        assert result.success
        assert result.data["dns_working"]
        assert result.data["hosts_resolved"] == 1
        assert "142.250.80.46" in result.data["results"][0]["ip_addresses"]

@pytest.mark.asyncio
async def test_dns_resolution_nxdomain():
    """Test NXDOMAIN handling."""
    diag = TestDNSResolution()
    
    mock_nslookup = """
Server:		192.168.1.1
Address:	192.168.1.1#53

** server can't find nonexistent.invalid: NXDOMAIN
"""
    
    with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.return_value.stdout = mock_nslookup
        mock_run.return_value.success = True
        
        result = await diag.run(hostnames=["nonexistent.invalid"])
        
        assert result.success
        assert not result.data["dns_working"]
        assert not result.data["results"][0]["resolved"]
        assert "NXDOMAIN" in result.data["results"][0]["error"]

@pytest.mark.asyncio
async def test_dns_resolution_with_custom_server():
    """Test using a custom DNS server."""
    diag = TestDNSResolution()
    
    mock_nslookup = """
Server:		8.8.8.8
Address:	8.8.8.8#53

Non-authoritative answer:
Name:	google.com
Address: 142.250.80.46
"""
    
    with patch.object(diag.executor, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.return_value.stdout = mock_nslookup
        mock_run.return_value.success = True
        
        result = await diag.run(hostnames=["google.com"], dns_server="8.8.8.8")
        
        assert result.success
        assert result.data["dns_server"] == "8.8.8.8"
```

## Implementation Notes

- Use `nslookup` for cross-platform compatibility (available on both macOS and Windows)
- On Windows, `Resolve-DnsName` provides cleaner output but is PowerShell-only
- Consider testing with system DNS first, then retry with public DNS if failed
- Time the resolution to identify slow DNS servers
- CNAME records may return intermediate names before final IP - handle this
- Some networks use DNS-based content filtering - be aware of false NXDOMAIN

## Related Functions

- `ping_dns`: Should succeed before this test (proves IP connectivity)
- `get_ip_config`: Contains the configured DNS servers
- `ping_gateway`: Required for basic connectivity

## Diagnostic Ladder Complete

With `test_dns_resolution` passing, the user has verified:

1. **Physical Layer**: Network adapter is up and connected
2. **Data Link Layer**: Valid MAC, link established
3. **Network Layer (Local)**: Valid IP, can reach gateway
4. **Network Layer (WAN)**: Can reach external IPs (8.8.8.8)
5. **Application Layer**: DNS resolution works

If all five pass, the network is healthy. The LLM should investigate application-specific issues (browser settings, firewall rules, specific website problems).

