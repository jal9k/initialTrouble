# Phase 1: Foundation

Project setup, TypeScript interfaces, and base configuration.

---

## Step 1: Initialize Next.js Project
Verify build its already created just make sure its created. 
```bash
cd /Users/tyurgal/Documents/python/diag/network-diag/frontend/techtime

# Create Next.js app with TypeScript
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*"

# Install dependencies
npm install clsx tailwind-merge lucide-react recharts nuqs react-markdown remark-gfm

# Install shadcn/ui
npx shadcn@latest init

# Add Claude theme
npx shadcn@latest add https://tweakcn.com/r/themes/claude.json
```

---

## Step 2: Add shadcn/ui Components

```bash
# Core components needed for Phase 1-3
npx shadcn@latest add button card input textarea label badge skeleton scroll-area separator tooltip

# Additional components for later phases
npx shadcn@latest add accordion collapsible dropdown-menu navigation-menu popover select sheet table tabs progress switch
```

---

## Step 3: Configure TypeScript

Update `tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

---

## Step 4: Create Types

Create `types/index.ts`:

```typescript
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
```

---

## Step 5: Create Root Layout

Create `app/layout.tsx`:

```typescript
// app/layout.tsx

import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { ThemeProvider } from '@/components/theme-provider'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Header } from '@/components/layout/Header'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Network Diagnostics',
  description: 'AI-powered network troubleshooting assistant'
}

export default function RootLayout({
  children
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <TooltipProvider>
            <div className="relative min-h-screen flex flex-col">
              <Header />
              <main className="flex-1">{children}</main>
            </div>
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
```

---

## Step 6: Create Theme Provider

Create `components/theme-provider.tsx`:

```typescript
// components/theme-provider.tsx

'use client'

import * as React from 'react'
import { ThemeProvider as NextThemesProvider } from 'next-themes'
import { type ThemeProviderProps } from 'next-themes/dist/types'

export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>
}
```

Install next-themes:

```bash
npm install next-themes
```

---

## Step 7: Create Skeleton Header

Create `components/layout/Header.tsx` (skeleton for now):

```typescript
// components/layout/Header.tsx

'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Moon, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'

const navItems = [
  { href: '/chat', label: 'Chat' },
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/history', label: 'History' }
]

export function Header({ className }: { className?: string }) {
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()

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
          <span className="font-bold">Network Diag</span>
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
          {/* Connection Status - Skeleton until WebSocket hook exists */}
          <Skeleton className="h-4 w-4 rounded-full" />

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

## Step 8: Create Home Page (Redirect)

Create `app/page.tsx`:

```typescript
// app/page.tsx

import { redirect } from 'next/navigation'

export default function HomePage() {
  redirect('/chat')
}
```

---

## Step 9: Create Skeleton Pages

Create `app/chat/page.tsx`:

```typescript
// app/chat/page.tsx

import { Skeleton } from '@/components/ui/skeleton'

export const metadata = {
  title: 'Chat - Network Diagnostics'
}

export default function ChatPage() {
  return (
    <div className="flex h-[calc(100vh-56px)]">
      {/* Sidebar skeleton */}
      <div className="hidden md:block w-64 border-r p-4 space-y-4">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-8 w-full" />
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        <div className="flex-1 p-4 flex items-center justify-center">
          <div className="text-center space-y-4">
            <Skeleton className="h-8 w-64 mx-auto" />
            <Skeleton className="h-4 w-48 mx-auto" />
            <div className="grid grid-cols-2 gap-2 max-w-md mx-auto mt-8">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          </div>
        </div>
        <div className="border-t p-4">
          <div className="flex gap-2">
            <Skeleton className="flex-1 h-11" />
            <Skeleton className="h-11 w-11" />
          </div>
        </div>
      </div>

      {/* Right panel skeleton */}
      <div className="hidden lg:block w-72 border-l p-4 space-y-4">
        <Skeleton className="h-6 w-32" />
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
        <Skeleton className="h-2 w-full mt-4" />
      </div>
    </div>
  )
}
```

Create `app/dashboard/page.tsx`:

```typescript
// app/dashboard/page.tsx

import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader } from '@/components/ui/card'

export const metadata = {
  title: 'Dashboard - Network Diagnostics'
}

export default function DashboardPage() {
  return (
    <div className="container py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Skeleton className="h-9 w-40 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Skeleton className="h-10 w-40" />
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-24" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-20 mb-1" />
              <Skeleton className="h-3 w-32" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts */}
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 2 }).map((_, i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-6 w-40" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-[300px] w-full" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Table */}
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-40" />
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
```

Create `app/history/page.tsx`:

```typescript
// app/history/page.tsx

import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent } from '@/components/ui/card'

export const metadata = {
  title: 'History - Network Diagnostics'
}

export default function HistoryPage() {
  return (
    <div className="container py-6">
      {/* Header */}
      <div className="mb-6">
        <Skeleton className="h-9 w-48 mb-2" />
        <Skeleton className="h-4 w-64" />
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <Skeleton className="h-10 flex-1" />
        <Skeleton className="h-10 w-40" />
        <Skeleton className="h-10 w-40" />
      </div>

      {/* Session cards */}
      <div className="space-y-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-4 w-full max-w-md" />
                  <div className="flex gap-2">
                    <Skeleton className="h-5 w-20" />
                    <Skeleton className="h-5 w-16" />
                  </div>
                </div>
                <Skeleton className="h-8 w-24" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Pagination */}
      <div className="flex justify-between mt-6">
        <Skeleton className="h-10 w-24" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-10 w-24" />
      </div>
    </div>
  )
}
```

---

## Step 10: Verify Phase 1

```bash
# Type check
npm run type-check || npx tsc --noEmit

# Lint
npm run lint

# Build
npm run build

# Start dev server to verify
npm run dev
```

---

## Phase 1 Checklist

- [ ] Next.js project initialized
- [ ] shadcn/ui installed with Claude theme
- [ ] All dependencies installed
- [ ] `types/index.ts` created with all interfaces
- [ ] `lib/utils.ts` exists (from shadcn init)
- [ ] Root layout with Header skeleton
- [ ] Theme provider configured
- [ ] Skeleton pages for /chat, /dashboard, /history
- [ ] Home page redirects to /chat
- [ ] `tsc --noEmit` passes
- [ ] `npm run lint` passes
- [ ] `npm run build` passes

**Gate: All checks must pass before proceeding to Phase 2.**

