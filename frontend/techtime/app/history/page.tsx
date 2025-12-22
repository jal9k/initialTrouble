import { HistoryPageClient } from './client'

export const metadata = {
  title: 'History - Network Diagnostics',
  description: 'Browse past diagnostic sessions'
}

// Mock data - would be fetched from API
const mockSessions = [
  {
    id: '1',
    startTime: new Date(Date.now() - 1000 * 60 * 30),
    outcome: 'resolved' as const,
    preview: 'WiFi keeps disconnecting every few minutes. Need help troubleshooting.',
    issueCategory: 'wifi' as const
  },
  {
    id: '2',
    startTime: new Date(Date.now() - 1000 * 60 * 60 * 2),
    outcome: 'resolved' as const,
    preview: 'Cannot access the internet, but local network works fine.',
    issueCategory: 'connectivity' as const
  },
  {
    id: '3',
    startTime: new Date(Date.now() - 1000 * 60 * 60 * 5),
    outcome: 'unresolved' as const,
    preview: 'DNS resolution failing intermittently.',
    issueCategory: 'dns' as const
  },
  {
    id: '4',
    startTime: new Date(Date.now() - 1000 * 60 * 60 * 24),
    outcome: 'resolved' as const,
    preview: 'No IP address being assigned to my computer.',
    issueCategory: 'ip_config' as const
  },
  {
    id: '5',
    startTime: new Date(Date.now() - 1000 * 60 * 60 * 48),
    outcome: 'abandoned' as const,
    preview: 'Slow network speeds when downloading files.',
    issueCategory: 'connectivity' as const
  },
  {
    id: '6',
    startTime: new Date(Date.now() - 1000 * 60 * 60 * 72),
    outcome: 'resolved' as const,
    preview: 'Cannot connect to work VPN.',
    issueCategory: 'connectivity' as const
  },
  {
    id: '7',
    startTime: new Date(Date.now() - 1000 * 60 * 60 * 96),
    outcome: 'in_progress' as const,
    preview: 'Network adapter keeps disabling itself.',
    issueCategory: 'wifi' as const
  }
]

export default function HistoryPage() {
  // In a real app, you would fetch data here:
  // const sessions = await listSessions({ pageSize: 50 })

  return <HistoryPageClient sessions={mockSessions} />
}
