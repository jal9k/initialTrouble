# TypeScript Interfaces

This document defines all TypeScript interfaces used throughout the Network Diagnostics frontend. All interfaces should be defined in `types/index.ts` and exported for use across components.

## File Location

```
frontend/
  types/
    index.ts        # All interfaces exported from here
```

---

## Core Interfaces

### Message Types

```typescript
/**
 * Represents the role of a message sender
 */
type MessageRole = 'user' | 'assistant' | 'system' | 'tool'

/**
 * A single chat message
 */
interface Message {
  id: string
  role: MessageRole
  content: string
  timestamp: Date
  toolCalls?: ToolCall[]
  toolResult?: ToolResult
}

/**
 * Tool call information from the AI
 */
interface ToolCall {
  id: string
  name: string
  arguments: Record<string, unknown>
}

/**
 * Result of a tool execution
 */
interface ToolResult {
  toolCallId: string
  name: string
  result: unknown
  error?: string
  duration?: number
}
```

### Session Types

```typescript
/**
 * Session outcome status
 */
type SessionOutcome = 'resolved' | 'unresolved' | 'abandoned' | 'in_progress'

/**
 * Network issue category
 */
type IssueCategory = 
  | 'connectivity'
  | 'dns'
  | 'wifi'
  | 'ip_config'
  | 'gateway'
  | 'unknown'

/**
 * A diagnostic session
 */
interface Session {
  id: string
  startTime: Date
  endTime?: Date
  outcome: SessionOutcome
  issueCategory?: IssueCategory
  messageCount: number
  toolsUsed: string[]
  summary?: string
}

/**
 * Session list item (lightweight for lists)
 */
interface SessionListItem {
  id: string
  startTime: Date
  outcome: SessionOutcome
  issueCategory?: IssueCategory
  preview: string  // First user message truncated
}
```

### Tool Types

```typescript
/**
 * Parameter definition for a diagnostic tool
 */
interface ToolParameter {
  name: string
  type: 'string' | 'number' | 'boolean'
  description: string
  required: boolean
  default?: unknown
}

/**
 * A diagnostic tool definition
 */
interface DiagnosticTool {
  name: string
  displayName: string
  description: string
  category: 'connectivity' | 'dns' | 'wifi' | 'ip_config' | 'system'
  parameters: ToolParameter[]
  osiLayer: number  // 1-5 for OSI layer mapping
}

/**
 * Tool execution status
 */
type ToolExecutionStatus = 'idle' | 'executing' | 'success' | 'error'

/**
 * Tool execution state
 */
interface ToolExecutionState {
  toolName: string
  status: ToolExecutionStatus
  startTime?: Date
  endTime?: Date
  result?: unknown
  error?: string
}
```

### OSI Layer Types

```typescript
/**
 * State of an OSI diagnostic layer
 */
type LayerStatus = 'pending' | 'testing' | 'pass' | 'fail' | 'skipped'

/**
 * OSI layer definition
 */
interface OSILayer {
  number: number
  name: string
  description: string
  tools: string[]  // Tool names that test this layer
}

/**
 * OSI layer state during diagnostics
 */
interface LayerState {
  layer: OSILayer
  status: LayerStatus
  testResult?: string
  testedAt?: Date
}

/**
 * The 5 diagnostic layers (simplified OSI)
 */
const DIAGNOSTIC_LAYERS: OSILayer[] = [
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
```

### Analytics Types

```typescript
/**
 * Summary statistics for the analytics dashboard
 */
interface SessionSummary {
  totalSessions: number
  resolvedCount: number
  unresolvedCount: number
  abandonedCount: number
  resolutionRate: number  // 0-1
  averageTimeToResolution: number  // milliseconds
  totalCost: number  // in dollars
}

/**
 * Tool usage statistics
 */
interface ToolStats {
  toolName: string
  executionCount: number
  successRate: number  // 0-1
  averageDuration: number  // milliseconds
  lastUsed: Date
}

/**
 * Time series data point for charts
 */
interface TimeSeriesPoint {
  timestamp: Date
  value: number
}

/**
 * Category breakdown for pie charts
 */
interface CategoryBreakdown {
  category: string
  count: number
  percentage: number
}
```

### WebSocket Types

```typescript
/**
 * WebSocket connection state
 */
type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error'

/**
 * Message sent from client to server
 */
interface ClientMessage {
  message: string
  conversation_id?: string
}

/**
 * Message received from server
 */
interface ServerMessage {
  response: string
  tool_calls: ToolCall[] | null
  conversation_id: string
}

/**
 * WebSocket error details
 */
interface WebSocketError {
  code: number
  reason: string
  timestamp: Date
}
```

### API Response Types

```typescript
/**
 * Generic API response wrapper
 */
interface ApiResponse<T> {
  data: T
  success: boolean
  error?: string
}

/**
 * Paginated list response
 */
interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}

/**
 * Health check response
 */
interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy'
  version: string
  uptime: number
}
```

---

## Component Props Interfaces

### Chat Components

```typescript
interface ChatWindowProps {
  className?: string
  initialConversationId?: string
  onSessionStart?: (sessionId: string) => void
  onSessionEnd?: (outcome: SessionOutcome) => void
}

interface MessageBubbleProps {
  message: Message
  isLatest?: boolean
  showTimestamp?: boolean
}

interface ToolExecutionCardProps {
  execution: ToolExecutionState
  onCancel?: () => void
  showDetails?: boolean
}
```

### Diagnostics Components

```typescript
interface OSILadderVizProps {
  layers: LayerState[]
  currentLayer?: number
  className?: string
  onLayerClick?: (layer: number) => void
}

interface ManualToolPanelProps {
  tools: DiagnosticTool[]
  onExecute: (toolName: string, params: Record<string, unknown>) => void
  className?: string
}

interface ToolCardProps {
  tool: DiagnosticTool
  isExpanded: boolean
  isExecuting: boolean
  onToggle: () => void
  onExecute: (params: Record<string, unknown>) => void
}
```

### Analytics Components

```typescript
interface SummaryCardsProps {
  summary: SessionSummary
  isLoading?: boolean
}

interface SessionsChartProps {
  data: TimeSeriesPoint[]
  chartType: 'line' | 'bar' | 'area'
  className?: string
}

interface ToolStatsTableProps {
  stats: ToolStats[]
  sortBy?: keyof ToolStats
  sortOrder?: 'asc' | 'desc'
  onSort?: (column: keyof ToolStats) => void
}
```

### Layout Components

```typescript
interface HeaderProps {
  className?: string
}

interface SidebarProps {
  sessions: SessionListItem[]
  activeSessionId?: string
  onSessionSelect: (sessionId: string) => void
  onNewSession: () => void
  isLoading?: boolean
}
```

---

## Utility Types

```typescript
/**
 * Make all properties optional recursively
 */
type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P]
}

/**
 * Extract the return type of an async function
 */
type AsyncReturnType<T extends (...args: unknown[]) => Promise<unknown>> =
  T extends (...args: unknown[]) => Promise<infer R> ? R : never

/**
 * Props that include children
 */
interface WithChildren {
  children: React.ReactNode
}

/**
 * Props that include className
 */
interface WithClassName {
  className?: string
}
```

---

## Type Guards

```typescript
/**
 * Check if a message has tool calls
 */
function hasToolCalls(message: Message): message is Message & { toolCalls: ToolCall[] } {
  return Array.isArray(message.toolCalls) && message.toolCalls.length > 0
}

/**
 * Check if a message is a tool result
 */
function isToolResult(message: Message): message is Message & { toolResult: ToolResult } {
  return message.role === 'tool' && message.toolResult !== undefined
}

/**
 * Check if session is active
 */
function isActiveSession(session: Session): boolean {
  return session.outcome === 'in_progress'
}
```

---

## Export Pattern

All types should be exported from a single entry point:

```typescript
// types/index.ts

// Core types
export type { Message, MessageRole, ToolCall, ToolResult }
export type { Session, SessionListItem, SessionOutcome, IssueCategory }
export type { DiagnosticTool, ToolParameter, ToolExecutionStatus, ToolExecutionState }
export type { OSILayer, LayerState, LayerStatus }
export type { SessionSummary, ToolStats, TimeSeriesPoint, CategoryBreakdown }
export type { ConnectionState, ClientMessage, ServerMessage, WebSocketError }
export type { ApiResponse, PaginatedResponse, HealthResponse }

// Component props
export type { ChatWindowProps, MessageBubbleProps, ToolExecutionCardProps }
export type { OSILadderVizProps, ManualToolPanelProps, ToolCardProps }
export type { SummaryCardsProps, SessionsChartProps, ToolStatsTableProps }
export type { HeaderProps, SidebarProps }

// Utility types
export type { DeepPartial, AsyncReturnType, WithChildren, WithClassName }

// Constants
export { DIAGNOSTIC_LAYERS }

// Type guards
export { hasToolCalls, isToolResult, isActiveSession }
```

---

## Test Specifications

### Type Compilation Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| All interfaces compile | `tsc --noEmit` passes with no errors |
| No implicit any | Strict mode catches missing types |
| Type exports accessible | All types importable from `@/types` |
| Type guards work | Guards correctly narrow types |

### Integration Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| API responses match types | Server responses conform to interfaces |
| WebSocket messages typed | All WS messages match defined types |
| Component props validated | TypeScript catches invalid props |

---

## Lint/Build Verification

- [ ] All interfaces defined in `types/index.ts`
- [ ] No `any` types used
- [ ] All exports properly typed
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All type guards have tests

**Gate:** Types must compile before any component implementation begins.

---

## Related Documents

- [api.md](../lib/api.md) - API client uses these types
- [websocket.md](../lib/websocket.md) - WebSocket types
- [headless-patterns.md](../headless-patterns.md) - Hook return types

