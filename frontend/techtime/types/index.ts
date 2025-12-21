// types/index.ts

// ============================================================================
// Message Types
// ============================================================================

export type MessageRole = 'user' | 'assistant' | 'system' | 'tool'

export interface Message {
  id: string
  role: MessageRole
  content: string
  timestamp: Date
  toolCalls?: ToolCall[]
  toolResult?: ToolResult
}

export interface ToolCall {
  id: string
  name: string
  arguments: Record<string, unknown>
}

export interface ToolResult {
  toolCallId: string
  name: string
  result: unknown
  error?: string
  duration?: number
}

// ============================================================================
// Session Types
// ============================================================================

export type SessionOutcome = 'resolved' | 'unresolved' | 'abandoned' | 'in_progress'

export type IssueCategory =
  | 'connectivity'
  | 'dns'
  | 'wifi'
  | 'ip_config'
  | 'gateway'
  | 'unknown'

export interface Session {
  id: string
  startTime: Date
  endTime?: Date
  outcome: SessionOutcome
  issueCategory?: IssueCategory
  messageCount: number
  toolsUsed: string[]
  summary?: string
}

export interface SessionListItem {
  id: string
  startTime: Date
  outcome: SessionOutcome
  issueCategory?: IssueCategory
  preview: string
}

// ============================================================================
// Tool Types
// ============================================================================

export interface ToolParameter {
  name: string
  type: 'string' | 'number' | 'boolean'
  description: string
  required: boolean
  default?: unknown
}

export interface DiagnosticTool {
  name: string
  displayName: string
  description: string
  category: 'connectivity' | 'dns' | 'wifi' | 'ip_config' | 'system'
  parameters: ToolParameter[]
  osiLayer: number
}

export type ToolExecutionStatus = 'idle' | 'executing' | 'success' | 'error'

export interface ToolExecutionState {
  toolName: string
  status: ToolExecutionStatus
  startTime?: Date
  endTime?: Date
  result?: unknown
  error?: string
}

// ============================================================================
// OSI Layer Types
// ============================================================================

export type LayerStatus = 'pending' | 'testing' | 'pass' | 'fail' | 'skipped'

export interface OSILayer {
  number: number
  name: string
  description: string
  tools: string[]
}

export interface LayerState {
  layer: OSILayer
  status: LayerStatus
  testResult?: string
  testedAt?: Date
}

export const DIAGNOSTIC_LAYERS: OSILayer[] = [
  {
    number: 1,
    name: 'Physical/Link',
    description: 'Network adapter and cable connectivity',
    tools: ['check_adapter_status']
  },
  {
    number: 2,
    name: 'IP Configuration',
    description: 'IP address and subnet configuration',
    tools: ['get_ip_config']
  },
  {
    number: 3,
    name: 'Gateway',
    description: 'Default gateway connectivity',
    tools: ['ping_gateway']
  },
  {
    number: 4,
    name: 'DNS',
    description: 'DNS resolution capability',
    tools: ['test_dns_resolution', 'ping_dns']
  },
  {
    number: 5,
    name: 'Internet',
    description: 'External connectivity',
    tools: ['ping_external']
  }
]

// ============================================================================
// Analytics Types
// ============================================================================

export interface SessionSummary {
  totalSessions: number
  resolvedCount: number
  unresolvedCount: number
  abandonedCount: number
  resolutionRate: number
  averageTimeToResolution: number
  totalCost: number
}

export interface ToolStats {
  toolName: string
  executionCount: number
  successRate: number
  averageDuration: number
  lastUsed: Date
}

export interface TimeSeriesPoint {
  timestamp: Date
  value: number
}

export interface CategoryBreakdown {
  category: string
  count: number
  percentage: number
}

// ============================================================================
// WebSocket Types
// ============================================================================

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error'

export interface ClientMessage {
  message: string
  conversation_id?: string
}

export interface ServerMessage {
  response: string
  tool_calls: ToolCall[] | null
  conversation_id: string
}

export interface WebSocketError {
  code: number
  reason: string
  timestamp: Date
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiResponse<T> {
  data: T
  success: boolean
  error?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy'
  version: string
  uptime: number
}

// ============================================================================
// Component Props Types
// ============================================================================

export interface ChatWindowProps {
  className?: string
  initialConversationId?: string
  onSessionStart?: (sessionId: string) => void
  onSessionEnd?: (outcome: SessionOutcome) => void
}

export interface MessageBubbleProps {
  message: Message
  isLatest?: boolean
  showTimestamp?: boolean
}

export interface ToolExecutionCardProps {
  execution: ToolExecutionState
  onCancel?: () => void
  showDetails?: boolean
}

export interface OSILadderVizProps {
  layers: LayerState[]
  currentLayer?: number
  className?: string
  onLayerClick?: (layer: number) => void
}

export interface ManualToolPanelProps {
  tools: DiagnosticTool[]
  onExecute: (toolName: string, params: Record<string, unknown>) => void
  className?: string
}

export interface ToolCardProps {
  tool: DiagnosticTool
  isExpanded: boolean
  isExecuting: boolean
  onToggle: () => void
  onExecute: (params: Record<string, unknown>) => void
}

export interface SummaryCardsProps {
  summary: SessionSummary
  isLoading?: boolean
}

export interface SessionsChartProps {
  data: TimeSeriesPoint[]
  chartType: 'line' | 'bar' | 'area'
  className?: string
}

export interface ToolStatsTableProps {
  stats: ToolStats[]
  sortBy?: keyof ToolStats
  sortOrder?: 'asc' | 'desc'
  onSort?: (column: keyof ToolStats) => void
}

export interface HeaderProps {
  className?: string
}

export interface SidebarProps {
  sessions: SessionListItem[]
  activeSessionId?: string
  onSessionSelect: (sessionId: string) => void
  onNewSession: () => void
  isLoading?: boolean
}

// ============================================================================
// Utility Types
// ============================================================================

export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P]
}

export interface WithChildren {
  children: React.ReactNode
}

export interface WithClassName {
  className?: string
}

// ============================================================================
// Type Guards
// ============================================================================

export function hasToolCalls(message: Message): message is Message & { toolCalls: ToolCall[] } {
  return Array.isArray(message.toolCalls) && message.toolCalls.length > 0
}

export function isToolResult(message: Message): message is Message & { toolResult: ToolResult } {
  return message.role === 'tool' && message.toolResult !== undefined
}

export function isActiveSession(session: Session): boolean {
  return session.outcome === 'in_progress'
}

