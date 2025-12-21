"""Network diagnostic functions."""

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

    # Register check_adapter_status
    registry.register(
        name="check_adapter_status",
        description="Check if network adapters are enabled and their connection status. "
        "Use this first to verify physical/link layer connectivity.",
        parameters=[
            ToolParameter(
                name="interface_name",
                type="string",
                description="Specific interface to check (e.g., 'en0', 'Ethernet'). "
                "If not provided, checks all interfaces.",
                required=False,
            ),
        ],
    )(check_adapter_status)

    # Register get_ip_config
    registry.register(
        name="get_ip_config",
        description="Get IP configuration including IP address, subnet, gateway, and DNS servers. "
        "Detects APIPA (169.254.x.x) addresses indicating DHCP failure.",
        parameters=[
            ToolParameter(
                name="interface_name",
                type="string",
                description="Specific interface to check. If not provided, checks all active interfaces.",
                required=False,
            ),
        ],
    )(get_ip_config)

    # Register ping_gateway
    registry.register(
        name="ping_gateway",
        description="Test connectivity to the default gateway (router) using ICMP ping. "
        "Verifies local network path is working.",
        parameters=[
            ToolParameter(
                name="gateway",
                type="string",
                description="Gateway IP to ping. If not provided, auto-detects from routing table.",
                required=False,
            ),
            ToolParameter(
                name="count",
                type="number",
                description="Number of ping packets to send (default: 4)",
                required=False,
            ),
        ],
    )(ping_gateway)

    # Register ping_dns
    registry.register(
        name="ping_dns",
        description="Test connectivity to external DNS servers (8.8.8.8, 1.1.1.1) using ICMP ping. "
        "Verifies internet/WAN connectivity independent of DNS resolution.",
        parameters=[
            ToolParameter(
                name="count",
                type="number",
                description="Number of ping packets per server (default: 4)",
                required=False,
            ),
        ],
    )(ping_dns)

    # Register test_dns_resolution
    registry.register(
        name="test_dns_resolution",
        description="Test DNS name resolution by resolving common hostnames. "
        "Verifies the system can translate domain names to IP addresses.",
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
                description="Specific DNS server to use. If not provided, uses system default.",
                required=False,
            ),
        ],
    )(test_dns_resolution)

    # Register enable_wifi
    registry.register(
        name="enable_wifi",
        description="Enable the WiFi adapter. Use this when WiFi is disabled and needs to be turned on. "
        "On macOS uses networksetup, on Windows uses netsh.",
        parameters=[
            ToolParameter(
                name="interface_name",
                type="string",
                description="Specific WiFi interface to enable. "
                "macOS default: en0, Windows default: Wi-Fi. "
                "Only specify if the default doesn't work.",
                required=False,
            ),
        ],
    )(enable_wifi)

