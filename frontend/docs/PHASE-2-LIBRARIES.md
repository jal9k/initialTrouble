# Phase 2: Libraries

API client, WebSocket client, and utility functions.

---

## Step 1: Create Utility Functions

Update `lib/utils.ts` (extends shadcn default):

```typescript
// lib/utils.ts

import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

// ============================================================================
// Class Name Utilities
// ============================================================================

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

// ============================================================================
// Date/Time Utilities
// ============================================================================

export function formatDate(
  date: Date | string,
  format: 'date' | 'time' | 'datetime' | 'relative' = 'date'
): string {
  const d = typeof date === 'string' ? new Date(date) : date

  switch (format) {
    case 'date':
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      })

    case 'time':
      return d.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit'
      })

    case 'datetime':
      return d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit'
      })

    case 'relative':
      return formatRelativeTime(d)
  }
}

export function formatRelativeTime(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHour = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHour / 24)

  if (diffSec < 60) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHour < 24) return `${diffHour}h ago`
  if (diffDay < 7) return `${diffDay}d ago`

  return formatDate(date, 'date')
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`

  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (hours > 0) {
    const remainingMin = minutes % 60
    return `${hours}h ${remainingMin}m`
  }

  if (minutes > 0) {
    const remainingSec = seconds % 60
    return `${minutes}m ${remainingSec}s`
  }

  return `${seconds}s`
}

// ============================================================================
// String Utilities
// ============================================================================

export function truncate(str: string, maxLength: number, suffix = '...'): string {
  if (str.length <= maxLength) return str
  return str.slice(0, maxLength - suffix.length) + suffix
}

export function capitalize(str: string): string {
  if (!str) return str
  return str.charAt(0).toUpperCase() + str.slice(1)
}

// ============================================================================
// Number Utilities
// ============================================================================

export function formatNumber(
  num: number,
  format: 'default' | 'percent' | 'currency' | 'compact' = 'default'
): string {
  switch (format) {
    case 'percent':
      return `${(num * 100).toFixed(1)}%`

    case 'currency':
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
      }).format(num)

    case 'compact':
      return new Intl.NumberFormat('en-US', {
        notation: 'compact',
        compactDisplay: 'short'
      }).format(num)

    default:
      return new Intl.NumberFormat('en-US').format(num)
  }
}

// ============================================================================
// ID Utilities
// ============================================================================

export function generateId(prefix?: string): string {
  const id = Math.random().toString(36).substring(2, 11)
  return prefix ? `${prefix}_${id}` : id
}

// ============================================================================
// Async Utilities
// ============================================================================

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout | null = null

  return (...args: Parameters<T>) => {
    if (timeoutId) clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), delay)
  }
}
```

---

## Step 2: Create API Client

Create `lib/api.ts`:

```typescript
// lib/api.ts

import type {
  HealthResponse,
  SessionListItem,
  Session,
  Message,
  SessionSummary,
  ToolStats,
  TimeSeriesPoint,
  CategoryBreakdown,
  DiagnosticTool,
  ToolResult,
  PaginatedResponse,
  SessionOutcome
} from '@/types'

// ============================================================================
// Configuration
// ============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface RequestConfig {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
  headers?: Record<string, string>
  cache?: RequestCache
  revalidate?: number
}

// ============================================================================
// Error Handling
// ============================================================================

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message)
    this.name = 'ApiError'
  }

  get isNotFound(): boolean {
    return this.status === 404
  }

  get isUnauthorized(): boolean {
    return this.status === 401
  }

  get isServerError(): boolean {
    return this.status >= 500
  }
}

// ============================================================================
// Base Request Function
// ============================================================================

async function apiRequest<T>(endpoint: string, config: RequestConfig = {}): Promise<T> {
  const { method = 'GET', body, headers = {}, cache, revalidate } = config

  const url = `${API_BASE_URL}${endpoint}`

  const response = await fetch(url, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers
    },
    body: body ? JSON.stringify(body) : undefined,
    cache,
    next: revalidate ? { revalidate } : undefined
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new ApiError(response.status, error.detail || 'Request failed')
  }

  return response.json()
}

// ============================================================================
// Health
// ============================================================================

export async function getHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>('/health')
}

// ============================================================================
// Sessions
// ============================================================================

export interface ListSessionsParams {
  page?: number
  pageSize?: number
  outcome?: SessionOutcome
  startDate?: Date
  endDate?: Date
}

export async function listSessions(
  params: ListSessionsParams = {}
): Promise<PaginatedResponse<SessionListItem>> {
  const searchParams = new URLSearchParams()

  if (params.page) searchParams.set('page', String(params.page))
  if (params.pageSize) searchParams.set('page_size', String(params.pageSize))
  if (params.outcome) searchParams.set('outcome', params.outcome)
  if (params.startDate) searchParams.set('start_date', params.startDate.toISOString())
  if (params.endDate) searchParams.set('end_date', params.endDate.toISOString())

  const query = searchParams.toString()
  return apiRequest<PaginatedResponse<SessionListItem>>(
    `/api/sessions${query ? `?${query}` : ''}`
  )
}

export async function getSession(id: string): Promise<Session> {
  return apiRequest<Session>(`/api/sessions/${id}`)
}

export async function getSessionMessages(id: string): Promise<Message[]> {
  return apiRequest<Message[]>(`/api/sessions/${id}/messages`)
}

// ============================================================================
// Analytics
// ============================================================================

export interface AnalyticsSummaryParams {
  startDate?: Date
  endDate?: Date
}

export async function getAnalyticsSummary(
  params: AnalyticsSummaryParams = {}
): Promise<SessionSummary> {
  const searchParams = new URLSearchParams()

  if (params.startDate) searchParams.set('start_date', params.startDate.toISOString())
  if (params.endDate) searchParams.set('end_date', params.endDate.toISOString())

  const query = searchParams.toString()
  return apiRequest<SessionSummary>(`/api/analytics/summary${query ? `?${query}` : ''}`)
}

export async function getToolStats(): Promise<ToolStats[]> {
  return apiRequest<ToolStats[]>('/api/analytics/tools')
}

export interface SessionsOverTimeParams {
  startDate: Date
  endDate: Date
  granularity?: 'hour' | 'day' | 'week'
}

export async function getSessionsOverTime(
  params: SessionsOverTimeParams
): Promise<TimeSeriesPoint[]> {
  const searchParams = new URLSearchParams({
    start_date: params.startDate.toISOString(),
    end_date: params.endDate.toISOString(),
    granularity: params.granularity || 'day'
  })

  return apiRequest<TimeSeriesPoint[]>(`/api/analytics/sessions-over-time?${searchParams}`)
}

export async function getCategoryBreakdown(): Promise<CategoryBreakdown[]> {
  return apiRequest<CategoryBreakdown[]>('/api/analytics/categories')
}

// ============================================================================
// Tools
// ============================================================================

export async function listTools(): Promise<DiagnosticTool[]> {
  return apiRequest<DiagnosticTool[]>('/api/tools')
}

export interface ExecuteToolParams {
  toolName: string
  parameters?: Record<string, unknown>
}

export async function executeTool(params: ExecuteToolParams): Promise<ToolResult> {
  return apiRequest<ToolResult>(`/api/tools/${params.toolName}/execute`, {
    method: 'POST',
    body: params.parameters || {}
  })
}
```

---

## Step 3: Create WebSocket Client

Create `lib/websocket.ts`:

```typescript
// lib/websocket.ts

import type { ClientMessage, ServerMessage, ConnectionState } from '@/types'

// ============================================================================
// Configuration
// ============================================================================

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'
const WS_ENDPOINT = '/ws'

export interface WebSocketConfig {
  url?: string
  reconnect?: boolean
  reconnectInterval?: number
  maxReconnectAttempts?: number
  onOpen?: () => void
  onClose?: (event: CloseEvent) => void
  onError?: (error: Event) => void
  onMessage?: (message: ServerMessage) => void
}

const DEFAULT_CONFIG = {
  url: `${WS_BASE_URL}${WS_ENDPOINT}`,
  reconnect: true,
  reconnectInterval: 3000,
  maxReconnectAttempts: 5
}

// ============================================================================
// WebSocket Client Class
// ============================================================================

export class ChatWebSocket {
  private socket: WebSocket | null = null
  private config: Required<WebSocketConfig>
  private reconnectAttempts = 0
  private reconnectTimeout: NodeJS.Timeout | null = null
  private messageQueue: ClientMessage[] = []

  constructor(config: WebSocketConfig = {}) {
    this.config = {
      ...DEFAULT_CONFIG,
      onOpen: config.onOpen || (() => {}),
      onClose: config.onClose || (() => {}),
      onError: config.onError || (() => {}),
      onMessage: config.onMessage || (() => {}),
      ...config
    } as Required<WebSocketConfig>
  }

  get state(): ConnectionState {
    if (!this.socket) return 'disconnected'

    switch (this.socket.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting'
      case WebSocket.OPEN:
        return 'connected'
      case WebSocket.CLOSING:
      case WebSocket.CLOSED:
      default:
        return 'disconnected'
    }
  }

  get isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN
  }

  connect(): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      this.socket = new WebSocket(this.config.url)

      this.socket.onopen = () => {
        this.reconnectAttempts = 0
        this.flushMessageQueue()
        this.config.onOpen()
      }

      this.socket.onclose = (event) => {
        this.config.onClose(event)
        if (event.code !== 1000) {
          this.handleReconnect()
        }
      }

      this.socket.onerror = (error) => {
        this.config.onError(error)
      }

      this.socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as ServerMessage
          this.config.onMessage(message)
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }
    } catch (err) {
      console.error('Failed to create WebSocket:', err)
    }
  }

  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }

    if (this.socket) {
      this.socket.close(1000, 'Client disconnect')
      this.socket = null
    }
  }

  send(message: ClientMessage): void {
    if (this.isConnected) {
      this.socket!.send(JSON.stringify(message))
    } else {
      this.messageQueue.push(message)
      if (this.state === 'disconnected') {
        this.connect()
      }
    }
  }

  private handleReconnect(): void {
    if (!this.config.reconnect) return
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }

    this.reconnectAttempts++

    this.reconnectTimeout = setTimeout(() => {
      this.connect()
    }, this.config.reconnectInterval)
  }

  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift()!
      this.send(message)
    }
  }
}

// ============================================================================
// Singleton Pattern
// ============================================================================

let instance: ChatWebSocket | null = null

export function getWebSocket(config?: WebSocketConfig): ChatWebSocket {
  if (!instance) {
    instance = new ChatWebSocket(config)
  }
  return instance
}

export function destroyWebSocket(): void {
  if (instance) {
    instance.disconnect()
    instance = null
  }
}
```

---

## Step 4: Create Environment Variables

Create `.env.local`:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

Create `.env.example`:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

---

## Step 5: Update Header with Connection Status

Update `components/layout/Header.tsx` to use WebSocket state (still skeleton until hooks exist):

```typescript
// components/layout/Header.tsx

'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Moon, Sun, Wifi, WifiOff } from 'lucide-react'
import { useTheme } from 'next-themes'
import { getWebSocket } from '@/lib/websocket'
import type { ConnectionState } from '@/types'

const navItems = [
  { href: '/chat', label: 'Chat' },
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/history', label: 'History' }
]

export function Header({ className }: { className?: string }) {
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected')

  useEffect(() => {
    const ws = getWebSocket({
      onOpen: () => setConnectionState('connected'),
      onClose: () => setConnectionState('disconnected'),
      onError: () => setConnectionState('error')
    })

    // Check initial state
    setConnectionState(ws.state)

    // Connect
    ws.connect()

    return () => {
      // Don't disconnect on unmount - keep connection alive
    }
  }, [])

  const isConnected = connectionState === 'connected'
  const isConnecting = connectionState === 'connecting'

  return (
    <header
      className={cn(
        'sticky top-0 z-50 w-full border-b',
        'bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60',
        className
      )}
    >
      <div className="container flex h-14 items-center">
        {/* Logo */}
        <Link href="/" className="mr-6 flex items-center space-x-2">
          <span className="font-bold">TechTim(e)</span>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex gap-6">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'text-sm font-medium transition-colors hover:text-primary',
                pathname === item.href ? 'text-primary' : 'text-muted-foreground'
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Actions */}
        <div className="flex items-center gap-2">
          {/* Connection Status */}
          <div className="flex items-center gap-1 text-sm">
            {isConnected ? (
              <Wifi className="h-4 w-4 text-green-500" />
            ) : isConnecting ? (
              <Wifi className="h-4 w-4 text-yellow-500 animate-pulse" />
            ) : (
              <WifiOff className="h-4 w-4 text-red-500" />
            )}
          </div>

          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            <span className="sr-only">Toggle theme</span>
          </Button>
        </div>
      </div>
    </header>
  )
}
```

---

## Step 6: Verify Phase 2

```bash
# Type check
npm run type-check || npx tsc --noEmit

# Lint
npm run lint

# Build
npm run build
```

---

## Phase 2 Checklist

- [ ] `lib/utils.ts` updated with all utility functions
- [ ] `lib/api.ts` created with all API functions
- [ ] `lib/websocket.ts` created with WebSocket client
- [ ] `.env.local` created with API URLs
- [ ] `.env.example` created for reference
- [ ] Header updated with real connection status
- [ ] `tsc --noEmit` passes
- [ ] `npm run lint` passes
- [ ] `npm run build` passes

**Gate: All checks must pass before proceeding to Phase 3.**

