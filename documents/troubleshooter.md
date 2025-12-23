Good use case. Ministral can act as the reasoning layer that decides which diagnostics to run and interprets results.

## Architecture Overview

```
User describes problem
        ↓
   Ministral 3B (CPU inference, quantized)
        ↓
   Decides which diagnostic function(s) to call
        ↓
   Executes system commands via Python
        ↓
   Returns results to Ministral
        ↓
   Ministral interprets and suggests next steps or fix
```

## Diagnostic Functions to Implement

| Function | Purpose |
|----------|---------|
| `check_adapter_status` | Is the NIC enabled? WiFi on? |
| `get_ip_config` | DHCP working? Valid IP or 169.254.x.x? |
| `ping_gateway` | Can reach the router? |
| `ping_dns` | Can reach DNS servers? |
| `test_dns_resolution` | Does DNS actually resolve names? |
| `check_proxy_settings` | Proxy misconfigured? |
| `check_wifi_signal` | Signal strength if wireless |
| `get_route_table` | Routing issues? |
| `check_firewall_rules` | Blocking outbound? |
| `test_port_connectivity` | Specific port blocked? |

## Project Structure

```
network-diag/
├── main.py              # Entry point, Ollama chat loop
├── tools.py             # Tool definitions for Ministral
├── diagnostics/
│   ├── __init__.py
│   ├── adapter.py       # NIC status checks
│   ├── ip_config.py     # IP/DHCP checks
│   ├── connectivity.py  # Ping tests
│   ├── dns.py           # DNS resolution
│   ├── wifi.py          # Wireless-specific
│   └── firewall.py      # Firewall checks
└── requirements.txt
```

## Phase 1: Minimal Viable Version

Start with these 5 functions to diagnose 80% of issues:

1. **check_adapter_status** - Is the network adapter enabled?
2. **get_ip_config** - Do we have a valid IP?
3. **ping_gateway** - Can we reach the router?
4. **ping_dns** - Can we reach external DNS (8.8.8.8)?
5. **test_dns_resolution** - Can we resolve google.com?

This covers the classic diagnostic ladder:
- Layer 1: Physical/adapter
- Layer 2: Link/IP assignment  
- Layer 3: Gateway reachability
- Layer 4: External reachability
- Layer 7: DNS/name resolution

## Next Steps

Want me to write the code for Phase 1? I'll create:
1. The tool definitions in Ollama's format
2. The diagnostic functions Powershell or bash depending on computer OS.
3. The main chat loop that handles function calling