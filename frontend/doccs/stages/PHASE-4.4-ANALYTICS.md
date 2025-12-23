# Phase 4.4: Analytics Components

Implementing SummaryCards, SessionsChart, CategoryChart, ToolUsageChart, ToolStatsTable, and DateRangePicker.

---

## Prerequisites

- Phase 4.3 completed
- recharts installed (from Phase 1)

---

## Step 1: Verify Dependencies

```bash
# recharts should already be installed
npm list recharts
```

---

## Step 2: Create SummaryCards Component

Create `components/analytics/SummaryCards.tsx`:

```typescript
// components/analytics/SummaryCards.tsx
'use client'

import { cn, formatNumber, formatDuration } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Clock,
  DollarSign,
  CheckCircle
} from 'lucide-react'
import type { SessionSummary } from '@/types'

interface MetricCardProps {
  title: string
  value: string
  description?: string
  icon: typeof Activity
  trend?: { value: number; isPositive: boolean }
  isLoading?: boolean
}

function MetricCard({
  title,
  value,
  description,
  icon: Icon,
  trend,
  isLoading
}: MetricCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-4" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-8 w-20 mb-1" />
          <Skeleton className="h-3 w-32" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold tracking-tight">{value}</div>
        {(description || trend) && (
          <div className="flex items-center gap-1 mt-1">
            {trend && (
              <>
                {trend.isPositive ? (
                  <TrendingUp className="h-3 w-3 text-green-600" />
                ) : (
                  <TrendingDown className="h-3 w-3 text-red-600" />
                )}
                <span
                  className={cn(
                    'text-xs font-medium',
                    trend.isPositive ? 'text-green-600' : 'text-red-600'
                  )}
                >
                  {trend.value}%
                </span>
              </>
            )}
            {description && (
              <span className="text-xs text-muted-foreground">
                {description}
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface SummaryCardsProps {
  summary: SessionSummary
  isLoading?: boolean
  className?: string
}

export function SummaryCards({
  summary,
  isLoading = false,
  className
}: SummaryCardsProps) {
  const metrics = [
    {
      title: 'Total Sessions',
      value: formatNumber(summary.totalSessions),
      icon: Activity,
      description: `${summary.resolvedCount} resolved`
    },
    {
      title: 'Resolution Rate',
      value: formatNumber(summary.resolutionRate, 'percent'),
      icon: CheckCircle,
      description: `${summary.unresolvedCount} unresolved`
    },
    {
      title: 'Avg Time to Resolution',
      value: formatDuration(summary.averageTimeToResolution),
      icon: Clock,
      description: 'per session'
    },
    {
      title: 'Total Cost',
      value: formatNumber(summary.totalCost, 'currency'),
      icon: DollarSign,
      description: 'API usage'
    }
  ]

  return (
    <div
      className={cn(
        'grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
        className
      )}
    >
      {metrics.map((metric) => (
        <MetricCard key={metric.title} {...metric} isLoading={isLoading} />
      ))}
    </div>
  )
}
```

---

## Step 3: Create Chart Components

Create `components/analytics/SessionsChart.tsx`:

```typescript
// components/analytics/SessionsChart.tsx
'use client'

import { useMemo } from 'react'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'
import { cn, formatDate, formatNumber } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { TimeSeriesPoint, CategoryBreakdown, ToolStats } from '@/types'

const CHART_COLORS = [
  'hsl(var(--chart-1, 220 70% 50%))',
  'hsl(var(--chart-2, 160 60% 45%))',
  'hsl(var(--chart-3, 30 80% 55%))',
  'hsl(var(--chart-4, 280 65% 60%))',
  'hsl(var(--chart-5, 340 75% 55%))'
]

function ChartSkeleton() {
  return (
    <div className="w-full h-[300px] flex items-center justify-center">
      <Skeleton className="w-full h-full" />
    </div>
  )
}

// ============================================================================
// Sessions Chart (Line/Area/Bar)
// ============================================================================

interface SessionsChartProps {
  data: TimeSeriesPoint[]
  chartType?: 'line' | 'bar' | 'area'
  title?: string
  isLoading?: boolean
  className?: string
}

export function SessionsChart({
  data,
  chartType = 'area',
  title = 'Sessions Over Time',
  isLoading = false,
  className
}: SessionsChartProps) {
  const formattedData = useMemo(
    () =>
      data.map((point) => ({
        ...point,
        date: formatDate(point.timestamp, 'date'),
        value: point.value
      })),
    [data]
  )

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <ChartSkeleton />
        </CardContent>
      </Card>
    )
  }

  if (data.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="w-full h-[300px] flex items-center justify-center text-muted-foreground">
            No data available
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="w-full h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            {chartType === 'area' ? (
              <AreaChart data={formattedData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis
                  tick={{ fontSize: 12 }}
                  tickFormatter={(v) => formatNumber(v, 'compact')}
                />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="hsl(var(--primary))"
                  fill="hsl(var(--primary))"
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
              </AreaChart>
            ) : chartType === 'bar' ? (
              <BarChart data={formattedData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="value" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
              </BarChart>
            ) : (
              <LineChart data={formattedData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            )}
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

// ============================================================================
// Category Chart (Pie)
// ============================================================================

interface CategoryChartProps {
  data: CategoryBreakdown[]
  title?: string
  isLoading?: boolean
  className?: string
}

export function CategoryChart({
  data,
  title = 'Issue Categories',
  isLoading = false,
  className
}: CategoryChartProps) {
  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <ChartSkeleton />
        </CardContent>
      </Card>
    )
  }

  if (data.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="w-full h-[300px] flex items-center justify-center text-muted-foreground">
            No data available
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="w-full h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="count"
                nameKey="category"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={({ category, percentage }) =>
                  `${category} (${percentage.toFixed(1)}%)`
                }
              >
                {data.map((entry, index) => (
                  <Cell
                    key={entry.category}
                    fill={CHART_COLORS[index % CHART_COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

// ============================================================================
// Tool Usage Chart (Horizontal Bar)
// ============================================================================

interface ToolUsageChartProps {
  data: ToolStats[]
  title?: string
  isLoading?: boolean
  className?: string
}

export function ToolUsageChart({
  data,
  title = 'Tool Usage',
  isLoading = false,
  className
}: ToolUsageChartProps) {
  const chartData = useMemo(
    () =>
      data
        .sort((a, b) => b.executionCount - a.executionCount)
        .slice(0, 10)
        .map((tool) => ({
          name: tool.toolName,
          count: tool.executionCount,
          successRate: tool.successRate
        })),
    [data]
  )

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <ChartSkeleton />
        </CardContent>
      </Card>
    )
  }

  if (data.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="w-full h-[300px] flex items-center justify-center text-muted-foreground">
            No data available
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="w-full h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis type="number" tick={{ fontSize: 12 }} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={120} />
              <Tooltip />
              <Bar dataKey="count" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
```

---

## Step 4: Create ToolStatsTable Component

Create `components/analytics/ToolStatsTable.tsx`:

```typescript
// components/analytics/ToolStatsTable.tsx
'use client'

import { useState, useMemo } from 'react'
import { cn, formatNumber, formatDuration, formatDate } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import type { ToolStats } from '@/types'

type SortableColumn = keyof ToolStats

function getSuccessRateStyle(rate: number): string {
  if (rate >= 0.9)
    return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
  if (rate >= 0.7)
    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
  return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
}

function TableSkeleton() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <TableRow key={i}>
          <TableCell><Skeleton className="h-4 w-32" /></TableCell>
          <TableCell><Skeleton className="h-4 w-16" /></TableCell>
          <TableCell><Skeleton className="h-4 w-16" /></TableCell>
          <TableCell><Skeleton className="h-4 w-16" /></TableCell>
          <TableCell><Skeleton className="h-4 w-16" /></TableCell>
        </TableRow>
      ))}
    </>
  )
}

interface ToolStatsTableProps {
  stats: ToolStats[]
  sortBy?: SortableColumn
  sortOrder?: 'asc' | 'desc'
  onSort?: (column: SortableColumn) => void
  isLoading?: boolean
  className?: string
}

export function ToolStatsTable({
  stats,
  sortBy: externalSortBy,
  sortOrder: externalSortOrder,
  onSort,
  isLoading = false,
  className
}: ToolStatsTableProps) {
  const [internalSortBy, setInternalSortBy] =
    useState<SortableColumn>('executionCount')
  const [internalSortOrder, setInternalSortOrder] = useState<'asc' | 'desc'>(
    'desc'
  )

  const sortBy = externalSortBy ?? internalSortBy
  const sortOrder = externalSortOrder ?? internalSortOrder

  const handleSort = (column: SortableColumn) => {
    if (onSort) {
      onSort(column)
    } else {
      if (column === internalSortBy) {
        setInternalSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
      } else {
        setInternalSortBy(column)
        setInternalSortOrder('desc')
      }
    }
  }

  const sortedStats = useMemo(() => {
    if (!stats.length) return []

    return [...stats].sort((a, b) => {
      let aVal: unknown = a[sortBy]
      let bVal: unknown = b[sortBy]

      if (sortBy === 'lastUsed') {
        aVal = new Date(aVal as Date).getTime()
        bVal = new Date(bVal as Date).getTime()
      }

      if ((aVal as number) < (bVal as number))
        return sortOrder === 'asc' ? -1 : 1
      if ((aVal as number) > (bVal as number))
        return sortOrder === 'asc' ? 1 : -1
      return 0
    })
  }, [stats, sortBy, sortOrder])

  const SortIcon = ({ column }: { column: SortableColumn }) => {
    if (column !== sortBy) {
      return <ArrowUpDown className="ml-1 h-4 w-4 text-muted-foreground" />
    }
    return sortOrder === 'asc' ? (
      <ArrowUp className="ml-1 h-4 w-4" />
    ) : (
      <ArrowDown className="ml-1 h-4 w-4" />
    )
  }

  const columns: { key: SortableColumn; label: string }[] = [
    { key: 'toolName', label: 'Tool Name' },
    { key: 'executionCount', label: 'Executions' },
    { key: 'successRate', label: 'Success Rate' },
    { key: 'averageDuration', label: 'Avg Duration' },
    { key: 'lastUsed', label: 'Last Used' }
  ]

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Tool Performance</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              {columns.map((col) => (
                <TableHead
                  key={col.key}
                  className="cursor-pointer select-none hover:bg-muted"
                  onClick={() => handleSort(col.key)}
                >
                  <div className="flex items-center">
                    {col.label}
                    <SortIcon column={col.key} />
                  </div>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableSkeleton />
            ) : sortedStats.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="text-center text-muted-foreground py-8"
                >
                  No tool statistics available
                </TableCell>
              </TableRow>
            ) : (
              sortedStats.map((stat) => (
                <TableRow key={stat.toolName}>
                  <TableCell className="font-mono text-sm">
                    {stat.toolName}
                  </TableCell>
                  <TableCell>{formatNumber(stat.executionCount)}</TableCell>
                  <TableCell>
                    <Badge
                      variant="secondary"
                      className={cn(
                        'font-mono',
                        getSuccessRateStyle(stat.successRate)
                      )}
                    >
                      {formatNumber(stat.successRate, 'percent')}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-sm">
                    {formatDuration(stat.averageDuration)}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDate(stat.lastUsed, 'relative')}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
```

---

## Step 5: Create DateRangePicker Component

Create `components/analytics/DateRangePicker.tsx`:

```typescript
// components/analytics/DateRangePicker.tsx
'use client'

import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { CalendarIcon } from 'lucide-react'

const presets = [
  { label: 'Last 7 days', value: '7' },
  { label: 'Last 30 days', value: '30' },
  { label: 'Last 90 days', value: '90' }
]

interface DateRangePickerProps {
  className?: string
}

export function DateRangePicker({ className }: DateRangePickerProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [preset, setPreset] = useState(searchParams.get('days') || '7')

  const handlePresetChange = (value: string) => {
    setPreset(value)
    const params = new URLSearchParams(searchParams)
    params.set('days', value)
    router.push(`/dashboard?${params}`)
  }

  return (
    <Select value={preset} onValueChange={handlePresetChange}>
      <SelectTrigger className={className}>
        <CalendarIcon className="mr-2 h-4 w-4" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {presets.map((p) => (
          <SelectItem key={p.value} value={p.value}>
            {p.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
```

---

## Step 6: Create Analytics Index Export

Create `components/analytics/index.ts`:

```typescript
// components/analytics/index.ts

export { SummaryCards } from './SummaryCards'
export { SessionsChart, CategoryChart, ToolUsageChart } from './SessionsChart'
export { ToolStatsTable } from './ToolStatsTable'
export { DateRangePicker } from './DateRangePicker'
```

---

## Step 7: Verify Phase 4.4

```bash
npx tsc --noEmit && npm run lint && npm run build
```

---

## Phase 4.4 Checklist

- [ ] SummaryCards with 4 metric cards
- [ ] SummaryCards loading state
- [ ] SessionsChart (line/area/bar)
- [ ] CategoryChart (pie)
- [ ] ToolUsageChart (horizontal bar)
- [ ] Charts handle empty data
- [ ] ToolStatsTable with sorting
- [ ] ToolStatsTable success rate colors
- [ ] DateRangePicker with presets
- [ ] `tsc --noEmit` passes
- [ ] `npm run lint` passes
- [ ] `npm run build` passes

**Gate: All checks must pass before proceeding to Phase 4.5**


