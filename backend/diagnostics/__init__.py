"""Diagnostic functions for TechTime.

Tool registration with decision-boundary descriptions for small language models.
Each tool description includes CALL WHEN and DO NOT CALL conditions to help
small models (3B parameters) make correct tool selection decisions.
"""

from .base import BaseDiagnostic, DiagnosticResult
from .platform import Platform, CommandExecutor, get_platform

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

    # Import diagnostic implementations - Network tools
    from .adapter import check_adapter_status
    from .ip_config import get_ip_config
    from .connectivity import ping_gateway, ping_dns
    from .dns import test_dns_resolution
    from .wifi import enable_wifi
    
    # Import cross-platform tools
    from .temp_files import cleanup_temp_files
    from .process_mgmt import kill_process
    from .vpn import test_vpn_connectivity
    
    # Import new cross-platform tools
    from .reachability import ping_address, traceroute
    from .bluetooth import toggle_bluetooth
    from .ip_reset import ip_release, ip_renew, flush_dns
    
    # Import Windows-specific tools (only on Windows)
    current_platform = get_platform()
    if current_platform == Platform.WINDOWS:
        from .windows.dell_audio import fix_dell_audio
        from .windows.office_repair import repair_office365
        from .windows.system_repair import run_dism_sfc
        from .windows.log_analysis import review_system_logs
        from .windows.robocopy import robocopy

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
- has_network_connection=true → Adapter works. Call get_ip_config next.
- has_network_connection=false → Call enable_wifi to enable WiFi, then re-run check_adapter_status.
- connected_count=0 → Call enable_wifi to try automatic fix, then verify with check_adapter_status.
- After enable_wifi, if still not connected → Tell user to manually select WiFi network.
- Check the suggestions field for ACTION items to call.""",
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
- packet_loss > 50% → WARN. Unstable connection.

PARAMETERS: gateway (string, optional) - Gateway IP to ping. count (number, optional) - Number of pings.""",
        parameters=[
            ToolParameter(
                name="gateway",
                type="string",
                description="Gateway IP address to ping. Leave empty to auto-detect default gateway.",
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
    
    # #region agent log - H-D: Log ping_gateway registration
    # Debug logging removed - was writing to hardcoded local path
    # #endregion

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
        description="""Enable/fix the WiFi network adapter.

CALL THIS TOOL WHEN:
- User says "fix wifi", "wifi broken", "wifi not working" → ENABLE IT
- User says "enable wifi", "turn on wifi", "start wifi"
- check_adapter_status showed WiFi status="down" or connected_count=0

DEFAULT: If user has a WiFi problem, call this tool to enable/fix it.

DO NOT CALL IF:
- Problem is with Bluetooth (use toggle_bluetooth instead)

OUTPUT MEANING:
- changed=true → WiFi enabled
- changed=false → WiFi was already enabled
- success=false → Failed, may need admin privileges""",
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

    # =========================================================================
    # TOOL 7: cleanup_temp_files
    # OSI Layer: Application
    # Position in sequence: MAINTENANCE TOOL (storage/app issues)
    # =========================================================================
    registry.register(
        name="cleanup_temp_files",
        description="""Remove temporary files to free disk space.

CALL THIS TOOL WHEN:
- User reports low disk space
- User says: "disk full", "running out of space", "need more storage"
- Application is behaving erratically (potential corrupted cache)
- General system maintenance requested

DO NOT CALL IF:
- User specifically mentions data files (this doesn't recover data)
- This is a network connectivity issue (use network tools instead)

OUTPUT MEANING:
- space_freed_mb > 100 → Significant space recovered
- space_freed_mb < 10 → System was already clean
- errors_count > 0 → Some files couldn't be deleted (may need admin)""",
        parameters=[
            ToolParameter(
                name="aggressive",
                type="boolean",
                description="If true, includes additional cache locations like browser caches. Default: false",
                required=False,
            ),
            ToolParameter(
                name="dry_run",
                type="boolean",
                description="If true, reports what would be deleted without deleting. Default: false",
                required=False,
            ),
        ],
    )(cleanup_temp_files)

    # =========================================================================
    # TOOL 8: kill_process
    # OSI Layer: Application
    # Position in sequence: ACTION TOOL (frozen apps)
    # =========================================================================
    registry.register(
        name="kill_process",
        description="""Terminate hung or problematic processes.

CALL THIS TOOL WHEN:
- User says: "app frozen", "program stuck", "can't close", "not responding"
- A process is consuming excessive CPU or memory
- Application won't close normally
- You need to restart a misbehaving service

DO NOT CALL IF:
- User hasn't specified which process to kill
- The issue is network-related (use network tools)
- This is a general "computer slow" issue (investigate first)

OUTPUT MEANING:
- killed_count > 0 → Processes terminated successfully
- protected_blocked_count > 0 → System processes were protected
- failed_count > 0 → Some processes need admin privileges or force=true""",
        parameters=[
            ToolParameter(
                name="process_name",
                type="string",
                description="Name of process to kill (e.g., 'chrome', 'Teams'). Case-insensitive.",
                required=False,
            ),
            ToolParameter(
                name="process_id",
                type="number",
                description="Specific PID to terminate. Use if name matching isn't precise enough.",
                required=False,
            ),
            ToolParameter(
                name="force",
                type="boolean",
                description="Use forceful termination (SIGKILL/-9). Default: false (graceful)",
                required=False,
            ),
        ],
    )(kill_process)

    # =========================================================================
    # TOOL 9: test_vpn_connectivity
    # OSI Layer: Network
    # Position in sequence: AFTER basic network tests pass
    # =========================================================================
    registry.register(
        name="test_vpn_connectivity",
        description="""Test VPN connection status and tunnel functionality.

CALL THIS TOOL WHEN:
- User says: "VPN connected but can't access internal resources"
- User says: "VPN not working", "can't reach internal site"
- Verifying VPN is properly connected
- Diagnosing split tunneling issues

DO NOT CALL IF:
- User has no VPN (this is for VPN-specific issues)
- Basic network connectivity hasn't been verified (run network tools first)
- This is a general internet issue (use ping_dns instead)

OUTPUT MEANING:
- vpn_connected=true → VPN tunnel is active
- vpn_connected=false → VPN not connected, need to connect first
- routes_active=false → VPN routes may be misconfigured
- dns_via_vpn=false → Potential DNS leak""",
        parameters=[
            ToolParameter(
                name="vpn_type",
                type="string",
                description="VPN type: 'wireguard', 'openvpn', 'ipsec', 'cisco', 'globalprotect'. Auto-detects if not specified.",
                required=False,
            ),
            ToolParameter(
                name="test_endpoint",
                type="string",
                description="Internal endpoint to test through VPN (e.g., '192.168.10.1'). Tests connectivity if provided.",
                required=False,
            ),
        ],
    )(test_vpn_connectivity)

    # =========================================================================
    # WINDOWS-SPECIFIC TOOLS (only registered on Windows)
    # =========================================================================
    if current_platform == Platform.WINDOWS:
        # =================================================================
        # TOOL 10: fix_dell_audio
        # OSI Layer: Application
        # Platform: Windows only
        # =================================================================
        registry.register(
            name="fix_dell_audio",
            description="""Fix Dell audio driver issues by removing and reinstalling drivers.

CALL THIS TOOL WHEN:
- User reports no audio on a DELL computer
- User says: "no sound on Dell", "speakers not working", "audio stopped"
- Audio was working but stopped after Windows update
- Realtek or Waves MaxxAudio driver issues suspected

DO NOT CALL IF:
- Computer is not a Dell system (tool will check)
- Audio issue is on macOS or Linux
- Issue is with headphones/Bluetooth (different troubleshooting)

OUTPUT MEANING:
- is_dell=false → Not a Dell system, use different approach
- removed_count > 0 → Drivers removed, REBOOT REQUIRED
- reboot_initiated=true → System will restart in 60 seconds""",
            parameters=[
                ToolParameter(
                    name="confirm_reboot",
                    type="boolean",
                    description="If true, automatically initiates reboot. Default: false (user must reboot manually)",
                    required=False,
                ),
                ToolParameter(
                    name="backup_driver",
                    type="boolean",
                    description="If true, backs up driver info before removal. Default: true",
                    required=False,
                ),
            ],
        )(fix_dell_audio)

        # =================================================================
        # TOOL 11: repair_office365
        # OSI Layer: Application
        # Platform: Windows only
        # =================================================================
        registry.register(
            name="repair_office365",
            description="""Run Microsoft 365 repair to fix application issues.

CALL THIS TOOL WHEN:
- User says: "Word crashes", "Excel won't open", "Office not working"
- Office applications crash or have missing features
- Office activation issues
- User sees: "Office needs to be repaired"

DO NOT CALL IF:
- Office is not installed
- Issue is with a non-Office application
- User is on macOS (Office for Mac has different repair)

OUTPUT MEANING:
- repair_initiated=true → Repair process started
- installation_type="MSI" → Tool doesn't support MSI, use Control Panel
- repair_type_used="quick" → Fast repair (10-15 min)
- repair_type_used="online" → Full repair (30-60 min)""",
            parameters=[
                ToolParameter(
                    name="repair_type",
                    type="string",
                    description="'quick' for fast local repair, 'online' for thorough cloud repair. Default: 'quick'",
                    required=False,
                ),
            ],
        )(repair_office365)

        # =================================================================
        # TOOL 12: run_dism_sfc
        # OSI Layer: Application
        # Platform: Windows only
        # =================================================================
        registry.register(
            name="run_dism_sfc",
            description="""Run DISM and SFC to repair Windows system file corruption.

CALL THIS TOOL WHEN:
- Windows is behaving erratically
- User sees: "missing DLL", "system files damaged"
- Windows Update fails repeatedly
- Blue screens hint at system file corruption
- After malware removal

DO NOT CALL IF:
- Issue is application-specific (not Windows itself)
- User is on macOS or Linux
- Not running as Administrator (tool will fail)

OUTPUT MEANING:
- dism_result="healthy" → Component store is clean
- dism_result="repaired" → DISM fixed corruption
- sfc_result="no_violations" → System files are intact
- sfc_result="repaired" → SFC fixed corrupt files
- reboot_required=true → Must restart to complete""",
            parameters=[
                ToolParameter(
                    name="run_dism",
                    type="boolean",
                    description="Run DISM /RestoreHealth first. Default: true",
                    required=False,
                ),
                ToolParameter(
                    name="run_sfc",
                    type="boolean",
                    description="Run SFC /scannow after DISM. Default: true",
                    required=False,
                ),
                ToolParameter(
                    name="check_only",
                    type="boolean",
                    description="Only scan for issues, don't repair. Default: false",
                    required=False,
                ),
            ],
        )(run_dism_sfc)

        # =================================================================
        # TOOL 13: review_system_logs
        # OSI Layer: Application
        # Platform: Windows only
        # =================================================================
        registry.register(
            name="review_system_logs",
            description="""Analyze Windows Event Viewer and crash dumps to diagnose issues.

CALL THIS TOOL WHEN:
- System crashes or freezes frequently
- User reports: "keeps crashing", "blue screen", "computer restarts randomly"
- After unexpected shutdowns
- Need to diagnose recurring issues

DO NOT CALL IF:
- Issue is clearly application-specific (check app logs instead)
- User is on macOS or Linux
- This is a network connectivity issue

OUTPUT MEANING:
- bsod_events found → Blue screens occurred, check driver updates
- reliability_score < 5 → System is unstable
- crash_dumps_found > 0 → Use WinDbg for detailed analysis
- critical_events found → Immediate attention needed""",
            parameters=[
                ToolParameter(
                    name="log_types",
                    type="array",
                    description="Which logs to analyze: 'event_viewer', 'crash_dumps', 'bsod', 'reliability'. Default: all",
                    required=False,
                ),
                ToolParameter(
                    name="time_range_hours",
                    type="number",
                    description="How far back to search in hours. Default: 72 (3 days)",
                    required=False,
                ),
                ToolParameter(
                    name="severity_filter",
                    type="string",
                    description="Minimum severity: 'info', 'warning', 'error', 'critical'. Default: 'error'",
                    required=False,
                ),
            ],
        )(review_system_logs)

        # =================================================================
        # TOOL 14: robocopy
        # OSI Layer: Application
        # Platform: Windows only
        # =================================================================
        registry.register(
            name="robocopy",
            description="""Robust file copy with retry logic for reliable file transfers.

CALL THIS TOOL WHEN:
- User needs to copy files reliably with retry on failure
- User says: "copy files", "backup folder", "move files to another drive"
- Large file transfers that may fail due to network issues
- User wants to mirror or sync directories

DO NOT CALL IF:
- User is on macOS or Linux (use rsync instead)
- Simple single-file copy (this is for directories/bulk operations)
- User wants to delete files (this is a copy tool)

OUTPUT MEANING:
- exit_code 0-7 → Success (varying levels of copied files)
- exit_code 8+ → Errors occurred
- files_copied > 0 → Files were transferred
- mirror=true → Destination now matches source exactly""",
            parameters=[
                ToolParameter(
                    name="source",
                    type="string",
                    description="Source directory path to copy from",
                    required=True,
                ),
                ToolParameter(
                    name="destination",
                    type="string",
                    description="Destination directory path to copy to",
                    required=True,
                ),
                ToolParameter(
                    name="files",
                    type="string",
                    description="File pattern to copy (e.g., '*.txt'). Default: all files",
                    required=False,
                ),
                ToolParameter(
                    name="retries",
                    type="number",
                    description="Number of retries on failure. Default: 3",
                    required=False,
                ),
                ToolParameter(
                    name="wait",
                    type="number",
                    description="Wait time between retries in seconds. Default: 10",
                    required=False,
                ),
                ToolParameter(
                    name="mirror",
                    type="boolean",
                    description="Mirror mode - make destination match source exactly. Default: false",
                    required=False,
                ),
                ToolParameter(
                    name="move",
                    type="boolean",
                    description="Move files instead of copy (deletes source). Default: false",
                    required=False,
                ),
            ],
        )(robocopy)

    # =========================================================================
    # NEW CROSS-PLATFORM TOOLS
    # =========================================================================

    # =========================================================================
    # TOOL 15: ping_address
    # OSI Layer: Network (Layer 3)
    # Platform: All (Windows, macOS, Linux)
    # =========================================================================
    registry.register(
        name="ping_address",
        description="""Ping any specified address (IP or hostname) to test reachability.

CALL THIS TOOL WHEN:
- User asks to check if a specific website/server is reachable
- User says: "can I reach google.com", "is server X online", "ping this address"
- Need to test connectivity to a specific host (not just gateway/DNS)
- Diagnosing whether a specific service is responding

DO NOT CALL IF:
- Testing gateway connectivity (use ping_gateway instead)
- Testing general internet (use ping_dns instead)
- Need DNS resolution test (use test_dns_resolution instead)

OUTPUT MEANING:
- reachable=true → Host is responding to ping
- reachable=false → Host not responding (may be blocking ICMP)
- packet_loss_percent > 0 → Intermittent connectivity
- avg_time_ms > 200 → High latency connection""",
        parameters=[
            ToolParameter(
                name="host",
                type="string",
                description="IP address or hostname to ping (e.g., 'google.com', '192.168.1.100')",
                required=True,
            ),
            ToolParameter(
                name="count",
                type="number",
                description="Number of ping packets to send. Default: 4",
                required=False,
            ),
        ],
    )(ping_address)

    # =========================================================================
    # TOOL 16: traceroute
    # OSI Layer: Network (Layer 3)
    # Platform: All (Windows, macOS, Linux)
    # =========================================================================
    registry.register(
        name="traceroute",
        description="""Trace the network path to a destination to identify where problems occur.

CALL THIS TOOL WHEN:
- User says: "why is connection slow to X", "where is the network problem"
- Need to identify which network hop is causing issues
- Diagnosing routing problems or high latency
- ping_address shows packet loss and you need to find where

DO NOT CALL IF:
- Just checking if host is reachable (use ping_address instead)
- Network adapter is down (run check_adapter_status first)
- Testing basic connectivity (use ping_gateway, ping_dns first)

OUTPUT MEANING:
- destination_reached=true → Full path traced successfully
- destination_reached=false → Route incomplete (firewall/routing issue)
- hop with high avg_time_ms → That network segment is slow
- hop with timed_out=true → That router not responding (may be normal)""",
        parameters=[
            ToolParameter(
                name="host",
                type="string",
                description="Destination IP or hostname to trace route to",
                required=True,
            ),
            ToolParameter(
                name="max_hops",
                type="number",
                description="Maximum number of hops to trace. Default: 30",
                required=False,
            ),
        ],
    )(traceroute)

    # =========================================================================
    # TOOL 17: toggle_bluetooth
    # OSI Layer: Physical/Link (Layer 1-2)
    # Platform: All (Windows, macOS, Linux)
    # =========================================================================
    registry.register(
        name="toggle_bluetooth",
        description="""Enable, disable, or check Bluetooth adapter status.

ACTION SELECTION - CRITICAL:
- User says "fix", "broken", "not working", "enable", "turn on" → use action: "on"
- User says "disable", "turn off" → use action: "off"  
- User ONLY asks "is it on?", "check status" → use action: "status"

DEFAULT: If user has a problem with Bluetooth, use action: "on" to fix it.

DO NOT CALL IF:
- Problem is with WiFi (use enable_wifi instead)

OUTPUT MEANING:
- bluetooth_enabled=true → Bluetooth adapter is on
- bluetooth_enabled=false → Bluetooth adapter is off
- changed=true → State was changed by this action""",
        parameters=[
            ToolParameter(
                name="action",
                type="string",
                description="'on' to ENABLE/FIX bluetooth (DEFAULT for problems), 'off' to disable, 'status' ONLY if user asks to check",
                required=True,
                enum=["on", "off", "status"],
            ),
            ToolParameter(
                name="interface",
                type="string",
                description="Specific Bluetooth adapter (optional, uses default if not specified)",
                required=False,
            ),
        ],
    )(toggle_bluetooth)

    # =========================================================================
    # TOOL 18: ip_release
    # OSI Layer: Network (Layer 3)
    # Platform: All (Windows, macOS, Linux)
    # =========================================================================
    registry.register(
        name="ip_release",
        description="""Release the current DHCP IP address to reset network configuration.

CALL THIS TOOL WHEN:
- User has IP conflict issues
- get_ip_config shows APIPA address (169.254.x.x) and restart didn't help
- Need to fully reset network configuration
- Part of network troubleshooting sequence when other fixes failed

DO NOT CALL IF:
- Network is working fine (this will disconnect the network!)
- User has a static IP (DHCP release won't work)
- First step in troubleshooting (try simpler fixes first)

OUTPUT MEANING:
- released=true → IP address released, network will be disconnected
- After release, MUST call ip_renew to get new IP
- May require admin privileges

IMPORTANT: After calling this, you MUST call ip_renew to restore connectivity.""",
        parameters=[
            ToolParameter(
                name="interface",
                type="string",
                description="Specific network interface (e.g., 'Ethernet', 'en0', 'eth0'). Default: all interfaces",
                required=False,
            ),
        ],
    )(ip_release)

    # =========================================================================
    # TOOL 19: ip_renew
    # OSI Layer: Network (Layer 3)
    # Platform: All (Windows, macOS, Linux)
    # =========================================================================
    registry.register(
        name="ip_renew",
        description="""Renew the DHCP IP address to get a fresh network configuration.

CALL THIS TOOL WHEN:
- After calling ip_release to restore connectivity
- DHCP lease issues (IP expired or conflicting)
- get_ip_config shows APIPA (169.254.x.x) address
- User says: "refresh my IP", "get new IP address"

DO NOT CALL IF:
- Network is working correctly
- User has a static IP configuration
- DHCP server is not available (router offline)

OUTPUT MEANING:
- renewed=true → New IP address obtained
- new_ip shows the assigned address
- May require admin privileges
- If fails, check if DHCP server (router) is reachable""",
        parameters=[
            ToolParameter(
                name="interface",
                type="string",
                description="Specific network interface (e.g., 'Ethernet', 'en0', 'eth0'). Default: all interfaces",
                required=False,
            ),
        ],
    )(ip_renew)

    # =========================================================================
    # TOOL 20: flush_dns
    # OSI Layer: Application (Layer 7)
    # Platform: All (Windows, macOS, Linux)
    # =========================================================================
    registry.register(
        name="flush_dns",
        description="""Clear the DNS resolver cache to fix DNS-related issues.

CALL THIS TOOL WHEN:
- User says: "website shows old content", "DNS not updating"
- User recently changed DNS settings
- test_dns_resolution fails for some sites but not others
- Stale DNS cache suspected (site works on phone but not computer)
- After malware removal that may have poisoned DNS cache

DO NOT CALL IF:
- DNS resolution is working correctly
- Issue is with internet connectivity (use ping_dns first)
- Problem is with all websites (likely not a cache issue)

OUTPUT MEANING:
- flushed=true → DNS cache cleared successfully
- After flush, try accessing the website again
- May require admin privileges on some systems""",
        parameters=[],
    )(flush_dns)
