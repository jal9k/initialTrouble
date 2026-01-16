import { ChatPageClient } from './client'
import type { DiagnosticTool } from '@/types'

export const metadata = {
  title: 'Chat - TechTim(e)',
  description: 'AI-powered L1 desktop support'
}

// Fallback tools data (used when API is unavailable or in static export mode)
const fallbackTools: DiagnosticTool[] = [
  // === Core Network Diagnostics (OSI Layer 1-5) ===
  {
    name: 'check_adapter_status',
    displayName: 'Check Adapter Status',
    description: 'Check if network adapters are enabled and their connection status.',
    category: 'connectivity' as const,
    parameters: [
      { name: 'interface_name', type: 'string' as const, description: 'Specific interface to check (e.g., "en0", "Ethernet"). Leave empty to check all.', required: false }
    ],
    osiLayer: 1
  },
  {
    name: 'get_ip_config',
    displayName: 'Get IP Configuration',
    description: 'Get IP configuration including IP address, subnet, gateway, and DNS servers.',
    category: 'ip_config' as const,
    parameters: [
      { name: 'interface_name', type: 'string' as const, description: 'Specific interface to check. Leave empty to check all active interfaces.', required: false }
    ],
    osiLayer: 2
  },
  {
    name: 'ping_gateway',
    displayName: 'Ping Gateway',
    description: 'Test connectivity to the default gateway (router) using ICMP ping.',
    category: 'connectivity' as const,
    parameters: [
      { name: 'gateway', type: 'string' as const, description: 'Gateway IP to ping. Leave empty to auto-detect.', required: false },
      { name: 'count', type: 'number' as const, description: 'Number of ping packets to send', required: false, default: 4 }
    ],
    osiLayer: 3
  },
  {
    name: 'ping_dns',
    displayName: 'Ping External (Internet)',
    description: 'Test internet connectivity by pinging external DNS servers (8.8.8.8, 1.1.1.1).',
    category: 'connectivity' as const,
    parameters: [
      { name: 'count', type: 'number' as const, description: 'Number of ping packets per server', required: false, default: 4 }
    ],
    osiLayer: 4
  },
  {
    name: 'test_dns_resolution',
    displayName: 'Test DNS Resolution',
    description: 'Test DNS name resolution by resolving hostnames.',
    category: 'dns' as const,
    parameters: [
      { name: 'hostnames', type: 'string' as const, description: 'Comma-separated hostnames to resolve (e.g., "google.com,cloudflare.com")', required: false },
      { name: 'dns_server', type: 'string' as const, description: 'Specific DNS server to use. Leave empty for system default.', required: false }
    ],
    osiLayer: 5
  },
  // === Connectivity & Reachability ===
  {
    name: 'ping_address',
    displayName: 'Ping Address',
    description: 'Ping any specified IP address or hostname.',
    category: 'connectivity' as const,
    parameters: [
      { name: 'host', type: 'string' as const, description: 'IP address or hostname to ping', required: true },
      { name: 'count', type: 'number' as const, description: 'Number of ping packets to send', required: false, default: 4 }
    ],
    osiLayer: 3
  },
  {
    name: 'traceroute',
    displayName: 'Traceroute',
    description: 'Trace the network path to a destination host.',
    category: 'connectivity' as const,
    parameters: [
      { name: 'host', type: 'string' as const, description: 'Destination IP or hostname', required: true },
      { name: 'max_hops', type: 'number' as const, description: 'Maximum number of hops', required: false, default: 30 }
    ],
    osiLayer: 3
  },
  {
    name: 'test_vpn_connectivity',
    displayName: 'Test VPN Connectivity',
    description: 'Check VPN connection status and test internal endpoint reachability.',
    category: 'vpn' as const,
    parameters: [
      { name: 'vpn_type', type: 'string' as const, description: 'VPN type (e.g., wireguard, openvpn)', required: false },
      { name: 'test_endpoint', type: 'string' as const, description: 'Internal endpoint to test (e.g., 10.0.0.1)', required: false }
    ],
    osiLayer: 3
  },
  // === Network Control Actions ===
  {
    name: 'enable_wifi',
    displayName: 'Enable/Disable WiFi',
    description: 'Enable or disable the WiFi adapter.',
    category: 'wifi' as const,
    parameters: [
      { name: 'action', type: 'string' as const, description: 'Action: "on" or "off"', required: false, default: 'on' },
      { name: 'interface', type: 'string' as const, description: 'Specific WiFi interface. Leave empty for default.', required: false }
    ],
    osiLayer: 1
  },
  {
    name: 'toggle_bluetooth',
    displayName: 'Toggle Bluetooth',
    description: 'Enable or disable Bluetooth adapter.',
    category: 'bluetooth' as const,
    parameters: [
      { name: 'action', type: 'string' as const, description: 'Action: "on" or "off"', required: false, default: 'on' }
    ],
    osiLayer: 1
  },
  {
    name: 'ip_release',
    displayName: 'Release IP Address',
    description: 'Release the current DHCP lease.',
    category: 'ip_config' as const,
    parameters: [
      { name: 'interface', type: 'string' as const, description: 'Network interface name', required: false }
    ],
    osiLayer: 2
  },
  {
    name: 'ip_renew',
    displayName: 'Renew IP Address',
    description: 'Request a new IP address from DHCP server.',
    category: 'ip_config' as const,
    parameters: [
      { name: 'interface', type: 'string' as const, description: 'Network interface name', required: false }
    ],
    osiLayer: 2
  },
  {
    name: 'flush_dns',
    displayName: 'Flush DNS Cache',
    description: 'Clear the local DNS resolver cache.',
    category: 'dns' as const,
    parameters: [],
    osiLayer: 4
  },
  // === System Utilities ===
  {
    name: 'cleanup_temp_files',
    displayName: 'Cleanup Temp Files',
    description: 'Remove temporary files and caches to free disk space.',
    category: 'maintenance' as const,
    parameters: [
      { name: 'dry_run', type: 'boolean' as const, description: 'Preview without deleting', required: false, default: false }
    ],
    osiLayer: 0
  },
  {
    name: 'kill_process',
    displayName: 'Kill Process',
    description: 'Terminate a running process by name or PID.',
    category: 'process' as const,
    parameters: [
      { name: 'process', type: 'string' as const, description: 'Process name or PID', required: true },
      { name: 'force', type: 'boolean' as const, description: 'Force kill (SIGKILL)', required: false, default: false }
    ],
    osiLayer: 0
  },
  // === Windows-Specific Tools ===
  {
    name: 'fix_dell_audio',
    displayName: 'Fix Dell Audio',
    description: 'Repair Dell/Realtek audio driver issues (Windows only).',
    category: 'windows' as const,
    parameters: [],
    osiLayer: 0
  },
  {
    name: 'repair_office365',
    displayName: 'Repair Office 365',
    description: 'Repair Microsoft Office 365 installation (Windows only).',
    category: 'windows' as const,
    parameters: [
      { name: 'quick_repair', type: 'boolean' as const, description: 'Use quick repair instead of online repair', required: false, default: true }
    ],
    osiLayer: 0
  },
  {
    name: 'run_dism_sfc',
    displayName: 'Run DISM/SFC',
    description: 'Run system file checker and DISM repair (Windows only).',
    category: 'windows' as const,
    parameters: [
      { name: 'sfc_only', type: 'boolean' as const, description: 'Run only SFC, skip DISM', required: false, default: false },
      { name: 'dism_only', type: 'boolean' as const, description: 'Run only DISM, skip SFC', required: false, default: false }
    ],
    osiLayer: 0
  },
  {
    name: 'review_system_logs',
    displayName: 'Review System Logs',
    description: 'Review Windows event logs for errors (Windows only).',
    category: 'windows' as const,
    parameters: [
      { name: 'log_name', type: 'string' as const, description: 'Log name: System, Application, or Security', required: false, default: 'System' },
      { name: 'hours', type: 'number' as const, description: 'Hours of history to review', required: false, default: 24 },
      { name: 'level', type: 'string' as const, description: 'Filter level: Error, Warning, or All', required: false, default: 'Error' }
    ],
    osiLayer: 0
  },
  {
    name: 'robocopy',
    displayName: 'Robocopy',
    description: 'Robust file copy operation (Windows only).',
    category: 'windows' as const,
    parameters: [
      { name: 'source', type: 'string' as const, description: 'Source directory path', required: true },
      { name: 'destination', type: 'string' as const, description: 'Destination directory path', required: true },
      { name: 'mirror', type: 'boolean' as const, description: 'Mirror mode (sync destination with source)', required: false, default: false }
    ],
    osiLayer: 0
  }
]

/**
 * Chat page - statically exportable.
 *
 * For static export compatibility, we don't fetch data at build time.
 * The client component fetches sessions dynamically on mount.
 * Tools are provided as static fallback data.
 */
export default function ChatPage() {
  // For static export, we pass empty sessions and fallback tools
  // The client component will fetch sessions dynamically after mount
  return (
    <ChatPageClient
      initialSessions={[]}
      tools={fallbackTools}
    />
  )
}
