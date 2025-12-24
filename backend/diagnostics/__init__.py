"""Diagnostic functions for TechTime.

Tool registration with decision-boundary descriptions for small language models.
Each tool description includes CALL WHEN and DO NOT CALL conditions to help
small models (3B parameters) make correct tool selection decisions.
"""

from .base import BaseDiagnostic, DiagnosticResult
from .platform import Platform, CommandExecutor

__all__ = [
    "BaseDiagnostic",
    "DiagnosticResult",
    "Platform",
    "CommandExecutor",
    "register_all_diagnostics",
]


def register_all_diagnostics(registry) -> None:
    """
    Register all diagnostic functions with the tool registry.

    This function imports and registers each diagnostic tool,
    making them available for LLM function calling.

    Each tool description follows this pattern:
    1. One-line summary of what the tool does
    2. CALL THIS TOOL WHEN: explicit trigger conditions
    3. DO NOT CALL IF: explicit exclusion conditions
    4. OUTPUT MEANING: interpretation guide for results

    Args:
        registry: ToolRegistry instance to register tools with
    """
    from ..tools.schemas import ToolParameter

    # Import diagnostic implementations
    from .adapter import check_adapter_status
    from .ip_config import get_ip_config
    from .connectivity import ping_gateway, ping_dns
    from .dns import test_dns_resolution
    from .wifi import enable_wifi

    # =========================================================================
    # TOOL 1: check_adapter_status
    # OSI Layer: Physical/Link (Layer 1-2)
    # Position in sequence: ALWAYS FIRST
    # =========================================================================
    registry.register(
        name="check_adapter_status",
        description="""Check if network adapters are enabled and connected.

CALL THIS TOOL WHEN:
- User reports ANY network problem (always run first)
- User says: "no internet", "can't connect", "offline", "network down"
- User says: "wifi not working", "ethernet not working"
- You need to verify physical connection before other diagnostics

DO NOT CALL IF:
- You already called this tool in the current session

OUTPUT MEANING:
- is_connected=true → Adapter works. Call get_ip_config next.
- is_connected=false → STOP. Tell user to connect to network.
- status="down" → STOP. Tell user to enable adapter.""",
        parameters=[
            ToolParameter(
                name="interface_name",
                type="string",
                description="Specific interface to check (e.g., 'en0', 'Ethernet'). "
                "Leave empty to check all interfaces.",
                required=False,
            ),
        ],
    )(check_adapter_status)

    # =========================================================================
    # TOOL 2: get_ip_config
    # OSI Layer: Network (Layer 3)
    # Position in sequence: SECOND (after check_adapter_status passes)
    # =========================================================================
    registry.register(
        name="get_ip_config",
        description="""Get IP address, subnet, gateway, and DNS configuration.

CALL THIS TOOL WHEN:
- check_adapter_status showed is_connected=true
- You need to verify the device has a valid IP address
- User mentions: "no IP", "DHCP not working", "169.254 address"

DO NOT CALL IF:
- check_adapter_status has not been run yet (run it first)
- check_adapter_status showed is_connected=false

OUTPUT MEANING:
- has_valid_ip=true AND has_gateway=true → Call ping_gateway next.
- is_apipa=true (169.254.x.x) → STOP. DHCP failed. Restart router.
- has_gateway=false → STOP. No gateway configured.""",
        parameters=[
            ToolParameter(
                name="interface_name",
                type="string",
                description="Specific interface to check. Leave empty to check all.",
                required=False,
            ),
        ],
    )(get_ip_config)

    # =========================================================================
    # TOOL 3: ping_gateway
    # OSI Layer: Network (Layer 3)
    # Position in sequence: THIRD (after get_ip_config passes)
    # =========================================================================
    registry.register(
        name="ping_gateway",
        description="""Test connectivity to the router/gateway using ping.

CALL THIS TOOL WHEN:
- get_ip_config showed valid IP and gateway exist
- You need to test if local network is working
- User says: "can't reach router", "slow network"

DO NOT CALL IF:
- check_adapter_status has not been run yet
- get_ip_config has not been run yet
- No valid IP or gateway exists

OUTPUT MEANING:
- reachable=true → Call ping_dns next.
- reachable=false → STOP. Router unreachable. Check cables, restart router.
- packet_loss > 50% → WARN. Unstable connection.""",
        parameters=[
            ToolParameter(
                name="gateway",
                type="string",
                description="Gateway IP to ping. Leave empty to auto-detect.",
                required=False,
            ),
            ToolParameter(
                name="count",
                type="number",
                description="Number of ping packets (default: 4)",
                required=False,
            ),
        ],
    )(ping_gateway)

    # =========================================================================
    # TOOL 4: ping_dns
    # OSI Layer: Network (Layer 3)
    # Position in sequence: FOURTH (after ping_gateway passes)
    # =========================================================================
    registry.register(
        name="ping_dns",
        description="""Test connectivity to external internet (8.8.8.8, 1.1.1.1).

CALL THIS TOOL WHEN:
- ping_gateway succeeded (router is reachable)
- You need to test if internet connectivity exists
- User says: "local network works but no internet"

DO NOT CALL IF:
- This is the first diagnostic (run check_adapter_status first)
- ping_gateway has not been run yet
- ping_gateway showed reachable=false

OUTPUT MEANING:
- internet_accessible=true → Call test_dns_resolution next.
- internet_accessible=false → STOP. ISP/modem issue. Restart modem.""",
        parameters=[
            ToolParameter(
                name="count",
                type="number",
                description="Number of ping packets per server (default: 4)",
                required=False,
            ),
        ],
    )(ping_dns)

    # =========================================================================
    # TOOL 5: test_dns_resolution
    # OSI Layer: Application (Layer 7)
    # Position in sequence: FIFTH/LAST (after ping_dns passes)
    # =========================================================================
    registry.register(
        name="test_dns_resolution",
        description="""Test if domain names can be resolved to IP addresses.

CALL THIS TOOL WHEN:
- ping_dns succeeded (internet is accessible via IP)
- User says: "websites won't load", "DNS error", "can't reach google.com"
- Browser shows: "DNS_PROBE_FINISHED_NXDOMAIN", "Server not found"

DO NOT CALL IF:
- This is the first diagnostic (run check_adapter_status first)
- ping_dns has not been run yet
- ping_dns showed internet_accessible=false

OUTPUT MEANING:
- dns_working=true → Network is fully functional.
- dns_working=false → STOP. Change DNS to 8.8.8.8 and 1.1.1.1.""",
        parameters=[
            ToolParameter(
                name="hostnames",
                type="array",
                description="Hostnames to resolve. Default: ['google.com', 'cloudflare.com']",
                required=False,
            ),
            ToolParameter(
                name="dns_server",
                type="string",
                description="Specific DNS server to use. Leave empty for system default.",
                required=False,
            ),
        ],
    )(test_dns_resolution)

    # =========================================================================
    # TOOL 6: enable_wifi
    # OSI Layer: Physical/Link (Layer 1-2)
    # Position in sequence: ACTION TOOL (called on user request)
    # =========================================================================
    registry.register(
        name="enable_wifi",
        description="""Enable the WiFi network adapter.

CALL THIS TOOL WHEN:
- User explicitly asks: "enable wifi", "turn on wifi", "start wifi"
- check_adapter_status showed WiFi status="down" (disabled)

DO NOT CALL IF:
- User did not ask to enable WiFi
- WiFi is already enabled (status="up")
- Problem is with Ethernet, not WiFi
- You are just running diagnostics (this tool changes system state)

OUTPUT MEANING:
- changed=true → WiFi enabled. Run check_adapter_status to verify.
- changed=false → WiFi was already enabled.
- success=false → Failed. May need admin privileges.

IMPORTANT: After calling this, run check_adapter_status and ping_dns to verify.""",
        parameters=[
            ToolParameter(
                name="interface_name",
                type="string",
                description="WiFi interface. macOS: en0, Windows: Wi-Fi. "
                "Only specify if default doesn't work.",
                required=False,
            ),
        ],
    )(enable_wifi)
