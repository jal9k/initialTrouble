import { ChatPageClient } from './client'
import { listSessions, listTools } from '@/lib/api'

export const metadata = {
  title: 'Chat - TechTim(e)',
  description: 'AI-powered L1 desktop support'
}

// Fallback tools data (used when API is unavailable)
const fallbackTools = [
  {
    name: 'check_adapter_status',
    displayName: 'Check Adapter Status',
    description: 'Check if network adapters are enabled and their connection status.',
    category: 'connectivity' as const,
    parameters: [
      {
        name: 'interface_name',
        type: 'string' as const,
        description: 'Specific interface to check (e.g., "en0", "Ethernet"). Leave empty to check all.',
        required: false
      }
    ],
    osiLayer: 1
  },
  {
    name: 'get_ip_config',
    displayName: 'Get IP Configuration',
    description: 'Get IP configuration including IP address, subnet, gateway, and DNS servers.',
    category: 'ip_config' as const,
    parameters: [
      {
        name: 'interface_name',
        type: 'string' as const,
        description: 'Specific interface to check. Leave empty to check all active interfaces.',
        required: false
      }
    ],
    osiLayer: 2
  },
  {
    name: 'ping_gateway',
    displayName: 'Ping Gateway',
    description: 'Test connectivity to the default gateway (router) using ICMP ping.',
    category: 'connectivity' as const,
    parameters: [
      {
        name: 'gateway',
        type: 'string' as const,
        description: 'Gateway IP to ping. Leave empty to auto-detect.',
        required: false
      },
      {
        name: 'count',
        type: 'number' as const,
        description: 'Number of ping packets to send',
        required: false,
        default: 4
      }
    ],
    osiLayer: 3
  },
  {
    name: 'test_dns_resolution',
    displayName: 'Test DNS Resolution',
    description: 'Test DNS name resolution by resolving hostnames.',
    category: 'dns' as const,
    parameters: [
      {
        name: 'hostnames',
        type: 'array' as const,
        description: 'Hostnames to resolve (e.g., ["google.com", "cloudflare.com"])',
        required: false
      },
      {
        name: 'dns_server',
        type: 'string' as const,
        description: 'Specific DNS server to use. Leave empty for system default.',
        required: false
      }
    ],
    osiLayer: 4
  },
  {
    name: 'ping_dns',
    displayName: 'Ping External (Internet)',
    description: 'Test internet connectivity by pinging external DNS servers (8.8.8.8, 1.1.1.1).',
    category: 'connectivity' as const,
    parameters: [
      {
        name: 'count',
        type: 'number' as const,
        description: 'Number of ping packets per server',
        required: false,
        default: 4
      }
    ],
    osiLayer: 5
  },
  {
    name: 'enable_wifi',
    displayName: 'Enable WiFi',
    description: 'Enable the WiFi adapter.',
    category: 'wifi' as const,
    parameters: [
      {
        name: 'interface_name',
        type: 'string' as const,
        description: 'Specific WiFi interface to enable. Leave empty for default.',
        required: false
      }
    ],
    osiLayer: 1
  }
]

export default async function ChatPage() {
  // Fetch sessions and tools from API
  let sessions = []
  let tools = fallbackTools
  
  try {
    const emptySessionsResponse = { items: [], total: 0, page: 1, pageSize: 20, hasMore: false }
    const [sessionsResult, toolsResult] = await Promise.all([
      listSessions({ pageSize: 20 }).catch(() => emptySessionsResponse),
      listTools().catch(() => fallbackTools)
    ])
    
    sessions = sessionsResult.items || []
    tools = toolsResult.length > 0 ? toolsResult : fallbackTools
  } catch {
    // Use fallback data if API is unavailable
    console.error('Failed to fetch data from API, using fallback')
  }

  return (
    <ChatPageClient
      initialSessions={sessions}
      tools={tools}
    />
  )
}
