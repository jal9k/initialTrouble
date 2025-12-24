# Dashboard Page

This document specifies the Dashboard page (`/dashboard`), the analytics overview.

## File Location

```
frontend/
  app/
    dashboard/
      page.tsx
```

---

## Overview

The Dashboard page provides:
- Summary metric cards
- Sessions over time chart
- Issue category breakdown
- Tool usage statistics
- Date range filtering

---

## Page Structure

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Header                                                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  Date Range: [Last 7 days ▼]                     [Refresh]              │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐       │
│  │ Total Sessions│ │Resolution Rate│ │ Avg Time      │ │ Total Cost    │       │
│  │     147       │ │    78.2%      │ │   4m 32s      │ │   $12.45      │       │
│  └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘       │
│                                                                                 │
│  ┌───────────────────────────────────────┐ ┌───────────────────────────────┐   │
│  │  Sessions Over Time                   │ │  Issue Categories             │   │
│  │  ╭─╮                                  │ │       ╭───────╮               │   │
│  │  │ ╰─╮   ╭──╮                         │ │    ╭──╯       ╰──╮            │   │
│  │ ─╯   ╰───╯  ╰─╮                       │ │    │             │            │   │
│  │               ╰──────────             │ │    ╰─╮         ╭─╯            │   │
│  │                                       │ │      ╰─────────╯              │   │
│  └───────────────────────────────────────┘ └───────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  Tool Performance                                                       │   │
│  │  ┌──────────────┬────────────┬──────────────┬──────────────┬──────┐    │   │
│  │  │ Tool Name    │ Executions │ Success Rate │ Avg Duration │ Last │    │   │
│  │  ├──────────────┼────────────┼──────────────┼──────────────┼──────┤    │   │
│  │  │ ping_gateway │    156     │    94.2%     │    235ms     │ 2h   │    │   │
│  │  │ test_dns     │    134     │    87.3%     │    1.2s      │ 5h   │    │   │
│  │  └──────────────┴────────────┴──────────────┴──────────────┴──────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Responsive Behavior

| Breakpoint | Layout |
|------------|--------|
| Desktop (lg+) | 2-column chart grid, full table |
| Tablet (md) | Stacked charts, scrollable table |
| Mobile (sm) | Single column, condensed table |

---

## Data Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Dashboard Page                                   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    Server Component                                  │ │
│  │                                                                      │ │
│  │  const summary = await getAnalyticsSummary()                        │ │
│  │  const toolStats = await getToolStats()                             │ │
│  │  const sessionsData = await getSessionsOverTime()                   │ │
│  │  const categories = await getCategoryBreakdown()                    │ │
│  │                                                                      │ │
│  └────────────────────────────┬────────────────────────────────────────┘ │
│                               │                                          │
│                               ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    Client Components                                 │ │
│  │                                                                      │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │ │
│  │  │  SummaryCards   │  │  SessionsChart  │  │  ToolStatsTable     │  │ │
│  │  │  (summary)      │  │  (sessionsData) │  │  (toolStats)        │  │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │ │
│  │                       ┌─────────────────┐                           │ │
│  │                       │  CategoryChart  │                           │ │
│  │                       │  (categories)   │                           │ │
│  │                       └─────────────────┘                           │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation

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
import { SessionsChart, CategoryChart, ToolUsageChart } from '@/components/analytics/SessionsChart'
import { ToolStatsTable } from '@/components/analytics/ToolStatsTable'
import { DateRangePicker } from '@/components/analytics/DateRangePicker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export const metadata = {
  title: 'Dashboard - TechTime',
  description: 'Analytics overview for TechTime'
}

// Revalidate every 5 minutes
export const revalidate = 300

async function SummarySection() {
  const summary = await getAnalyticsSummary()
  return <SummaryCards summary={summary} />
}

async function ChartsSection() {
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
      <CategoryChart
        data={categories}
        title="Issue Categories"
      />
    </div>
  )
}

async function ToolsSection() {
  const toolStats = await getToolStats()
  return <ToolStatsTable stats={toolStats} />
}

export default function DashboardPage() {
  return (
    <div className="container py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Analytics overview for TechTime
          </p>
        </div>
        <DateRangePicker />
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
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-40" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-40" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
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
```

---

## Date Range Picker

```typescript
// components/analytics/DateRangePicker.tsx
'use client'

import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { format } from 'date-fns'
import { Calendar } from '@/components/ui/calendar'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger
} from '@/components/ui/popover'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { CalendarIcon } from 'lucide-react'

const presets = [
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 90 days', days: 90 },
  { label: 'Custom', days: 0 }
]

export function DateRangePicker() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [preset, setPreset] = useState('7')

  const handlePresetChange = (value: string) => {
    setPreset(value)
    const days = parseInt(value)
    if (days > 0) {
      const params = new URLSearchParams(searchParams)
      params.set('days', value)
      router.push(`/dashboard?${params}`)
    }
  }

  return (
    <Select value={preset} onValueChange={handlePresetChange}>
      <SelectTrigger className="w-40">
        <CalendarIcon className="mr-2 h-4 w-4" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {presets.map(p => (
          <SelectItem key={p.days} value={String(p.days)}>
            {p.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
```

---

## Loading State

```typescript
// app/dashboard/loading.tsx
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export default function DashboardLoading() {
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
              <Skeleton className="h-8 w-20" />
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
          <Skeleton className="h-64 w-full" />
        </CardContent>
      </Card>
    </div>
  )
}
```

---

## Error Handling

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

## Test Specifications

### Page Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Page renders | All sections visible |
| Summary cards show data | 4 cards with values |
| Charts render | Line and pie charts displayed |
| Table shows data | Tool rows with stats |

### Data Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Server fetches data | API calls made |
| Loading shows skeletons | Suspense boundaries work |
| Error shows message | Error boundary catches |

### Interaction Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Date range changes | Data refetches |
| Table sorts | Rows reorder |
| Chart hovers | Tooltips appear |

### Responsive Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Desktop shows grid | 2-column charts |
| Mobile stacks | Single column |

---

## Lint/Build Verification

- [ ] Server components fetch correctly
- [ ] Suspense boundaries work
- [ ] Charts render without errors
- [ ] Table sorts properly
- [ ] Date picker works
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All tests pass

---

## Related Documents

- [SummaryCards.md](../analytics/SummaryCards.md) - Metric cards
- [SessionsChart.md](../analytics/SessionsChart.md) - Chart components
- [ToolStatsTable.md](../analytics/ToolStatsTable.md) - Stats table
- [api.md](../../lib/api.md) - API functions

