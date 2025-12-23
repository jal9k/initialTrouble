# Phase 4.5: Page Implementation

Implementing all pages with full functionality.

---

## Prerequisites

- All components from Phase 4.1-4.4 completed
- nuqs installed for URL state

---

## Step 1: Install nuqs (if not already)

```bash
npm install nuqs
```

---

## Step 2: Create Home Page

Update `app/page.tsx`:

```typescript
// app/page.tsx
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle
} from '@/components/ui/card'
import { MessageSquare, BarChart3, History, ArrowRight } from 'lucide-react'

export const metadata = {
  title: 'Network Diagnostics',
  description: 'AI-powered network troubleshooting assistant'
}

const features = [
  {
    title: 'Chat',
    description: 'Start a new diagnostic session with our AI assistant',
    icon: MessageSquare,
    href: '/chat'
  },
  {
    title: 'Dashboard',
    description: 'View analytics, metrics, and tool performance',
    icon: BarChart3,
    href: '/dashboard'
  },
  {
    title: 'History',
    description: 'Browse and continue past diagnostic sessions',
    icon: History,
    href: '/history'
  }
]

export default function HomePage() {
  return (
    <div className="container py-12">
      {/* Hero Section */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold tracking-tight mb-4">
          Network Diagnostics
        </h1>
        <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
          AI-powered troubleshooting for your network issues. Describe your
          problem and get step-by-step diagnostic assistance.
        </p>
        <Link href="/chat">
          <Button size="lg">
            Start New Session
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </Link>
      </div>

      {/* Feature Cards */}
      <div className="grid gap-6 md:grid-cols-3 max-w-4xl mx-auto">
        {features.map((feature) => (
          <Link key={feature.href} href={feature.href}>
            <Card className="h-full hover:border-primary/50 transition-colors cursor-pointer">
              <CardHeader>
                <feature.icon className="h-8 w-8 text-primary mb-2" />
                <CardTitle>{feature.title}</CardTitle>
                <CardDescription>{feature.description}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>

      {/* Footer text */}
      <div className="mt-16 text-center">
        <p className="text-sm text-muted-foreground">
          Powered by AI diagnostics across 5 network layers
        </p>
      </div>
    </div>
  )
}
```

---

## Step 3: Create Chat Page

Create `app/chat/page.tsx`:

```typescript
// app/chat/page.tsx
import { Suspense } from 'react'
import { ChatPageClient } from './client'
import { listSessions, listTools } from '@/lib/api'
import { Skeleton } from '@/components/ui/skeleton'

export const metadata = {
  title: 'Chat - Network Diagnostics',
  description: 'AI-powered network troubleshooting'
}

async function ChatContent() {
  try {
    const [sessionsResult, toolsResult] = await Promise.all([
      listSessions({ pageSize: 20 }),
      listTools()
    ])

    return (
      <ChatPageClient
        initialSessions={sessionsResult.items}
        tools={toolsResult}
      />
    )
  } catch {
    // Return with empty data on error
    return <ChatPageClient initialSessions={[]} tools={[]} />
  }
}

export default function ChatPage() {
  return (
    <Suspense fallback={<ChatLoading />}>
      <ChatContent />
    </Suspense>
  )
}

function ChatLoading() {
  return (
    <div className="flex h-[calc(100vh-56px)]">
      <div className="hidden md:block w-64 border-r p-4 space-y-4">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-8 w-full" />
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
      <div className="flex-1 p-4 flex items-center justify-center">
        <Skeleton className="h-8 w-64" />
      </div>
    </div>
  )
}
```

Create `app/chat/client.tsx`:

```typescript
// app/chat/client.tsx
'use client'

import { useState, useCallback } from 'react'
import { useChat } from '@/hooks/use-chat'
import { useOSILadder } from '@/hooks/use-osi-ladder'
import { useManualToolPanel } from '@/hooks/use-manual-tool-panel'
import { Sidebar } from '@/components/layout/Sidebar'
import { MobileSidebar } from '@/components/layout/MobileSidebar'
import { ChatWindow } from '@/components/chat/ChatWindow'
import { OSILadderViz } from '@/components/diagnostics/OSILadderViz'
import { ManualToolPanel } from '@/components/diagnostics/ManualToolPanel'
import type { SessionListItem, DiagnosticTool } from '@/types'

interface ChatPageClientProps {
  initialSessions: SessionListItem[]
  tools: DiagnosticTool[]
}

export function ChatPageClient({
  initialSessions,
  tools
}: ChatPageClientProps) {
  const [sessions, setSessions] = useState(initialSessions)
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)

  // Chat state
  const chat = useChat({
    onSessionStart: (id) => {
      setActiveSessionId(id)
      setSessions((prev) => [
        {
          id,
          startTime: new Date(),
          outcome: 'in_progress',
          preview: 'New conversation...'
        },
        ...prev
      ])
    }
  })

  // OSI ladder state
  const osiLadder = useOSILadder({
    onLayerChange: (layer, status) => {
      console.log(`Layer ${layer} is now ${status}`)
    }
  })

  // Manual tool panel state
  const toolPanel = useManualToolPanel({
    tools,
    onExecutionComplete: (result) => {
      const tool = tools.find((t) => t.name === result.name)
      if (tool) {
        if (result.error) {
          osiLadder.failLayer(tool.osiLayer, result.error)
        } else {
          osiLadder.passLayer(tool.osiLayer, JSON.stringify(result.result))
        }
      }
    }
  })

  const handleSessionSelect = useCallback(
    (sessionId: string) => {
      setActiveSessionId(sessionId)
      chat.loadConversation(sessionId)
    },
    [chat]
  )

  const handleNewSession = useCallback(() => {
    chat.startNewConversation()
    osiLadder.reset()
    setActiveSessionId(null)
  }, [chat, osiLadder])

  return (
    <div className="h-[calc(100vh-56px)]">
      {/* Mobile sidebar trigger */}
      <div className="md:hidden p-2 border-b">
        <MobileSidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSessionSelect={handleSessionSelect}
          onNewSession={handleNewSession}
        />
      </div>

      <div className="flex h-full">
        {/* Desktop Sidebar */}
        <div className="hidden md:block">
          <Sidebar
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSessionSelect={handleSessionSelect}
            onNewSession={handleNewSession}
          />
        </div>

        {/* Main Chat */}
        <div className="flex-1 min-w-0">
          <ChatWindow
            initialConversationId={activeSessionId ?? undefined}
            onSessionStart={chat.onSessionStart}
            onSessionEnd={chat.onSessionEnd}
          />
        </div>

        {/* Right Panel - Desktop only */}
        <div className="hidden lg:flex lg:flex-col lg:w-72 border-l">
          {/* OSI Ladder */}
          <div className="p-4 border-b">
            <h3 className="font-semibold text-sm mb-3">Diagnostic Progress</h3>
            <OSILadderViz
              layers={osiLadder.layers}
              currentLayer={osiLadder.currentLayer}
              showResults
            />
          </div>

          {/* Manual Tools */}
          <div className="flex-1 overflow-hidden">
            <ManualToolPanel
              tools={tools}
              onExecute={toolPanel.executeTool}
              results={toolPanel.results}
              executingTool={toolPanel.executingTool}
              onClearAll={toolPanel.clearAllResults}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
```

Create `app/chat/error.tsx`:

```typescript
// app/chat/error.tsx
'use client'

export default function ChatError({
  error,
  reset
}: {
  error: Error
  reset: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center h-[calc(100vh-56px)]">
      <h2 className="text-xl font-semibold mb-4">Something went wrong</h2>
      <p className="text-muted-foreground mb-4">{error.message}</p>
      <button
        onClick={reset}
        className="px-4 py-2 bg-primary text-primary-foreground rounded"
      >
        Try again
      </button>
    </div>
  )
}
```

---

## Step 4: Create Dashboard Page

Update `app/dashboard/page.tsx`:

```typescript
// app/dashboard/page.tsx
import { Suspense } from 'react'
import {
  getAnalyticsSummary,
  getToolStats,
  getSessionsOverTime,
  getCategoryBreakdown
} from '@/lib/api'
import { SummaryCards } from '@/components/analytics/SummaryCards'
import {
  SessionsChart,
  CategoryChart
} from '@/components/analytics/SessionsChart'
import { ToolStatsTable } from '@/components/analytics/ToolStatsTable'
import { DateRangePicker } from '@/components/analytics/DateRangePicker'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export const metadata = {
  title: 'Dashboard - Network Diagnostics',
  description: 'Analytics overview for network diagnostics'
}

export const revalidate = 300 // Revalidate every 5 minutes

async function SummarySection() {
  try {
    const summary = await getAnalyticsSummary()
    return <SummaryCards summary={summary} />
  } catch {
    return (
      <SummaryCards
        summary={{
          totalSessions: 0,
          resolvedCount: 0,
          unresolvedCount: 0,
          abandonedCount: 0,
          resolutionRate: 0,
          averageTimeToResolution: 0,
          totalCost: 0
        }}
      />
    )
  }
}

async function ChartsSection() {
  try {
    const [sessionsData, categories] = await Promise.all([
      getSessionsOverTime({
        startDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
        endDate: new Date(),
        granularity: 'day'
      }),
      getCategoryBreakdown()
    ])

    return (
      <div className="grid gap-4 md:grid-cols-2">
        <SessionsChart
          data={sessionsData}
          chartType="area"
          title="Sessions Over Time"
        />
        <CategoryChart data={categories} title="Issue Categories" />
      </div>
    )
  } catch {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <SessionsChart data={[]} title="Sessions Over Time" />
        <CategoryChart data={[]} title="Issue Categories" />
      </div>
    )
  }
}

async function ToolsSection() {
  try {
    const toolStats = await getToolStats()
    return <ToolStatsTable stats={toolStats} />
  } catch {
    return <ToolStatsTable stats={[]} />
  }
}

function SummaryCardsSkeleton() {
  return (
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
  )
}

function ChartsSkeleton() {
  return (
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
  )
}

function TableSkeleton() {
  return (
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
  )
}

export default function DashboardPage() {
  return (
    <div className="container py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Analytics overview for network diagnostics
          </p>
        </div>
        <DateRangePicker className="w-40" />
      </div>

      {/* Summary Cards */}
      <Suspense fallback={<SummaryCardsSkeleton />}>
        <SummarySection />
      </Suspense>

      {/* Charts */}
      <Suspense fallback={<ChartsSkeleton />}>
        <ChartsSection />
      </Suspense>

      {/* Tool Stats Table */}
      <Suspense fallback={<TableSkeleton />}>
        <ToolsSection />
      </Suspense>
    </div>
  )
}
```

Create `app/dashboard/error.tsx`:

```typescript
// app/dashboard/error.tsx
'use client'

import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-react'

export default function DashboardError({
  error,
  reset
}: {
  error: Error
  reset: () => void
}) {
  return (
    <div className="container py-6">
      <div className="flex flex-col items-center justify-center h-96">
        <h2 className="text-xl font-semibold mb-2">Failed to load analytics</h2>
        <p className="text-muted-foreground mb-4">{error.message}</p>
        <Button onClick={reset}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Retry
        </Button>
      </div>
    </div>
  )
}
```

---

## Step 5: Create History Page

Update `app/history/page.tsx`:

```typescript
// app/history/page.tsx
import { Suspense } from 'react'
import { listSessions } from '@/lib/api'
import { HistoryClient } from './client'
import { Skeleton } from '@/components/ui/skeleton'

export const metadata = {
  title: 'History - Network Diagnostics',
  description: 'Browse past diagnostic sessions'
}

interface SearchParams {
  page?: string
  outcome?: string
  category?: string
  search?: string
}

async function SessionList({ searchParams }: { searchParams: SearchParams }) {
  try {
    const sessions = await listSessions({
      page: parseInt(searchParams.page || '1'),
      pageSize: 10,
      outcome: searchParams.outcome as 'resolved' | 'unresolved' | 'abandoned' | undefined
    })

    return (
      <HistoryClient
        initialSessions={sessions.items}
        total={sessions.total}
        page={sessions.page}
        pageSize={sessions.pageSize}
        hasMore={sessions.hasMore}
      />
    )
  } catch {
    return (
      <HistoryClient
        initialSessions={[]}
        total={0}
        page={1}
        pageSize={10}
        hasMore={false}
      />
    )
  }
}

function HistoryLoading() {
  return (
    <div className="space-y-4">
      <div className="flex gap-4 mb-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-10 w-32" />
        <Skeleton className="h-10 w-32" />
      </div>
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-32 w-full" />
      ))}
    </div>
  )
}

export default function HistoryPage({
  searchParams
}: {
  searchParams: SearchParams
}) {
  return (
    <div className="container py-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Session History</h1>
        <p className="text-muted-foreground">
          Browse and continue past diagnostic sessions
        </p>
      </div>

      <Suspense fallback={<HistoryLoading />}>
        <SessionList searchParams={searchParams} />
      </Suspense>
    </div>
  )
}
```

Create `app/history/client.tsx`:

```typescript
// app/history/client.tsx
'use client'

import { useRouter } from 'next/navigation'
import { useQueryState } from 'nuqs'
import { cn, formatDate, truncate } from '@/lib/utils'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Search, ChevronLeft, ChevronRight, ArrowRight } from 'lucide-react'
import Link from 'next/link'
import type { SessionListItem, SessionOutcome } from '@/types'

const outcomeBadgeStyles: Record<SessionOutcome, string> = {
  resolved: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  unresolved:
    'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  abandoned: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
  in_progress: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
}

interface HistoryClientProps {
  initialSessions: SessionListItem[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}

export function HistoryClient({
  initialSessions,
  total,
  page,
  pageSize,
  hasMore
}: HistoryClientProps) {
  const router = useRouter()
  const [search, setSearch] = useQueryState('search')
  const [outcome, setOutcome] = useQueryState('outcome')
  const [category, setCategory] = useQueryState('category')
  const [pageNum, setPageNum] = useQueryState('page')

  const totalPages = Math.ceil(total / pageSize)

  const handleSearch = (value: string) => {
    setSearch(value || null)
    setPageNum('1')
  }

  const handleOutcomeChange = (value: string) => {
    setOutcome(value === 'all' ? null : value)
    setPageNum('1')
  }

  const handleCategoryChange = (value: string) => {
    setCategory(value === 'all' ? null : value)
    setPageNum('1')
  }

  const handlePageChange = (newPage: number) => {
    setPageNum(String(newPage))
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search sessions..."
            value={search || ''}
            onChange={(e) => handleSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        <Select value={outcome || 'all'} onValueChange={handleOutcomeChange}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Outcome" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Outcomes</SelectItem>
            <SelectItem value="resolved">Resolved</SelectItem>
            <SelectItem value="unresolved">Unresolved</SelectItem>
            <SelectItem value="abandoned">Abandoned</SelectItem>
          </SelectContent>
        </Select>

        <Select value={category || 'all'} onValueChange={handleCategoryChange}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            <SelectItem value="connectivity">Connectivity</SelectItem>
            <SelectItem value="dns">DNS</SelectItem>
            <SelectItem value="wifi">WiFi</SelectItem>
            <SelectItem value="ip_config">IP Config</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Session List */}
      <div className="space-y-4">
        {initialSessions.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              No sessions found matching your criteria
            </CardContent>
          </Card>
        ) : (
          initialSessions.map((session) => (
            <SessionCard key={session.id} session={session} />
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={() => handlePageChange(page - 1)}
            disabled={page <= 1}
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            Previous
          </Button>

          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>

          <Button
            variant="outline"
            onClick={() => handlePageChange(page + 1)}
            disabled={!hasMore}
          >
            Next
            <ChevronRight className="h-4 w-4 ml-2" />
          </Button>
        </div>
      )}
    </div>
  )
}

function SessionCard({ session }: { session: SessionListItem }) {
  return (
    <Card className="hover:border-primary/50 transition-colors">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm text-muted-foreground">
                {formatDate(session.startTime, 'datetime')}
              </span>
            </div>

            <p className="text-sm mb-3">"{truncate(session.preview, 100)}"</p>

            <div className="flex flex-wrap gap-2">
              <Badge
                variant="secondary"
                className={outcomeBadgeStyles[session.outcome]}
              >
                {session.outcome.replace('_', ' ')}
              </Badge>

              {session.issueCategory && (
                <Badge variant="outline">
                  {session.issueCategory.replace('_', ' ')}
                </Badge>
              )}
            </div>
          </div>

          <Link href={`/chat?session=${session.id}`}>
            <Button variant="ghost" size="sm">
              Continue
              <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}
```

---

## Step 6: Verify Phase 4.5

```bash
# Type check
npx tsc --noEmit

# Lint
npm run lint

# Build
npm run build

# Development server for manual testing
npm run dev
```

---

## Phase 4.5 Checklist

- [ ] Home page with feature cards
- [ ] Home page links work
- [ ] Chat page three-column layout
- [ ] Chat page mobile responsive
- [ ] Chat page session selection works
- [ ] Chat page OSI ladder updates
- [ ] Dashboard page loads data
- [ ] Dashboard charts render
- [ ] Dashboard date picker works
- [ ] History page filters work
- [ ] History page pagination works
- [ ] History page search works
- [ ] All error boundaries work
- [ ] All loading states work
- [ ] `tsc --noEmit` passes
- [ ] `npm run lint` passes
- [ ] `npm run build` passes

---

## Final Verification

After completing all Phase 4 sub-phases:

```bash
# Full verification
npx tsc --noEmit && npm run lint && npm run build

# Start development server
npm run dev

# Test all routes:
# - http://localhost:3000 (Home)
# - http://localhost:3000/chat (Chat)
# - http://localhost:3000/dashboard (Dashboard)
# - http://localhost:3000/history (History)
```

---

## Phase 4 Complete Checklist

### Phase 4.1: Layout
- [ ] Header with mobile menu
- [ ] Sidebar with session list
- [ ] MobileSidebar

### Phase 4.2: Chat
- [ ] MessageBubble with markdown
- [ ] ToolExecutionCard
- [ ] ChatWindow with all features

### Phase 4.3: Diagnostics
- [ ] OSILadderViz
- [ ] ToolCard
- [ ] ManualToolPanel

### Phase 4.4: Analytics
- [ ] SummaryCards
- [ ] SessionsChart / CategoryChart / ToolUsageChart
- [ ] ToolStatsTable
- [ ] DateRangePicker

### Phase 4.5: Pages
- [ ] Home page
- [ ] Chat page (full layout)
- [ ] Dashboard page
- [ ] History page

### Final
- [ ] All TypeScript errors resolved
- [ ] All ESLint errors resolved
- [ ] Build succeeds
- [ ] Manual testing complete

**Phase 4 Complete!**


