# SessionsChart Component

This document specifies the SessionsChart component for displaying analytics visualizations.

## File Location

```
frontend/
  components/
    analytics/
      SessionsChart.tsx
```

---

## Overview

The SessionsChart component displays:
- Sessions over time (line/area chart)
- Issue category breakdown (pie chart)
- Tool usage frequency (bar chart)

Uses Recharts library for visualizations.

---

## Props Interface

```typescript
interface SessionsChartProps {
  /** Time series data for sessions */
  data: TimeSeriesPoint[]
  
  /** Type of chart to render */
  chartType: 'line' | 'bar' | 'area'
  
  /** Chart title */
  title?: string
  
  /** Loading state */
  isLoading?: boolean
  
  /** Additional CSS classes */
  className?: string
}

interface CategoryChartProps {
  /** Category breakdown data */
  data: CategoryBreakdown[]
  
  /** Chart title */
  title?: string
  
  /** Loading state */
  isLoading?: boolean
  
  /** Additional CSS classes */
  className?: string
}

interface ToolUsageChartProps {
  /** Tool stats for chart */
  data: ToolStats[]
  
  /** Chart title */
  title?: string
  
  /** Loading state */
  isLoading?: boolean
  
  /** Additional CSS classes */
  className?: string
}
```

---

## Component Structure

### Sessions Over Time
```
┌─────────────────────────────────────────────────────────────┐
│  Sessions Over Time                                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │     ╭─╮                                               │  │
│  │   ╭─╯ ╰─╮   ╭──╮                                     │  │
│  │ ╭─╯     ╰───╯  ╰─╮     ╭─╮                          │  │
│  │─╯                 ╰─────╯ ╰──────────────────────    │  │
│  │                                                       │  │
│  │ Dec 1    Dec 7    Dec 14    Dec 21                   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Category Breakdown
```
┌─────────────────────────────────────────────────────────────┐
│  Issue Categories                                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         ╭───────╮                                     │  │
│  │      ╭──╯       ╰──╮       ■ Connectivity (45%)      │  │
│  │    ╭─╯             ╰─╮     ■ DNS (25%)               │  │
│  │    │                 │     ■ WiFi (20%)              │  │
│  │    ╰─╮             ╭─╯     ■ Other (10%)             │  │
│  │      ╰──╮       ╭──╯                                  │  │
│  │         ╰───────╯                                     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Tool Usage
```
┌─────────────────────────────────────────────────────────────┐
│  Tool Usage                                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ping_gateway     ████████████████████████    156      │  │
│  │ test_dns         ██████████████████          134      │  │
│  │ check_adapter    ██████████████              112      │  │
│  │ get_ip_config    ████████████                98       │  │
│  │ ping_dns         ████████                    67       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component States

| State | Description | Visual |
|-------|-------------|--------|
| Loading | Data fetching | Skeleton placeholder |
| Default | Data loaded | Chart rendered |
| Empty | No data | Empty state message |
| Hover | Data point hover | Tooltip with details |

---

## Behaviors

### Interactivity
- Hover tooltips with data values
- Click for drill-down (optional)
- Responsive sizing

### Data Formatting
- Dates formatted on x-axis
- Numbers abbreviated for large values
- Percentages for pie slices

---

## Dependencies

| Package | Usage |
|---------|-------|
| `recharts` | Chart library |

### shadcn/ui Dependencies

| Component | Usage |
|-----------|-------|
| `Card` | Chart container |
| `Skeleton` | Loading state |

---

## Styling Guidelines

### Chart Container
```css
.chart-container {
  @apply w-full h-[300px];
}

.chart-card {
  @apply p-4;
}

.chart-title {
  @apply text-lg font-semibold mb-4;
}
```

### Chart Theme
```typescript
// Use CSS variables for theme consistency
const chartTheme = {
  colors: {
    primary: 'hsl(var(--primary))',
    secondary: 'hsl(var(--secondary))',
    muted: 'hsl(var(--muted))'
  },
  fontFamily: 'inherit',
  fontSize: 12
}
```

---

## Implementation

```typescript
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
  'hsl(var(--chart-1))',
  'hsl(var(--chart-2))',
  'hsl(var(--chart-3))',
  'hsl(var(--chart-4))',
  'hsl(var(--chart-5))'
]

function ChartSkeleton() {
  return (
    <div className="w-full h-[300px] flex items-center justify-center">
      <Skeleton className="w-full h-full" />
    </div>
  )
}

export function SessionsChart({
  data,
  chartType,
  title = 'Sessions Over Time',
  isLoading = false,
  className
}: SessionsChartProps) {
  const formattedData = useMemo(() =>
    data.map(point => ({
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

  const ChartComponent = chartType === 'area' ? AreaChart : chartType === 'bar' ? BarChart : LineChart
  const DataComponent = chartType === 'area' ? Area : chartType === 'bar' ? Bar : Line

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="w-full h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <ChartComponent data={formattedData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(value) => formatNumber(value, 'compact')}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px'
                }}
                labelStyle={{ color: 'hsl(var(--foreground))' }}
              />
              <DataComponent
                type="monotone"
                dataKey="value"
                stroke="hsl(var(--primary))"
                fill="hsl(var(--primary))"
                fillOpacity={chartType === 'area' ? 0.2 : 1}
                strokeWidth={2}
              />
            </ChartComponent>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
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

export function ToolUsageChart({
  data,
  title = 'Tool Usage',
  isLoading = false,
  className
}: ToolUsageChartProps) {
  const chartData = useMemo(() =>
    data
      .sort((a, b) => b.executionCount - a.executionCount)
      .slice(0, 10)
      .map(tool => ({
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
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 12 }}
                width={120}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px'
                }}
              />
              <Bar
                dataKey="count"
                fill="hsl(var(--primary))"
                radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
```

---

## Accessibility

| Feature | Implementation |
|---------|---------------|
| Keyboard nav | Chart focusable |
| Screen reader | Data table alternative |
| Color contrast | Chart colors meet WCAG |
| Reduced motion | No animations when preferred |

---

## Test Specifications

### Render Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Line chart renders | Line path drawn |
| Area chart renders | Filled area shown |
| Bar chart renders | Bars displayed |
| Pie chart renders | Slices shown |
| Loading shows skeleton | Skeleton visible |
| Empty shows message | "No data" message |

### Data Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Dates formatted | X-axis shows readable dates |
| Values formatted | Large numbers abbreviated |
| Percentages shown | Pie labels include % |
| Top 10 shown | Bar chart limited |

### Interaction Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Hover shows tooltip | Data values displayed |
| Responsive sizing | Chart resizes with container |

---

## Lint/Build Verification

- [ ] Component properly typed
- [ ] Recharts imported correctly
- [ ] Theme colors used
- [ ] Responsive container works
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All tests pass

---

## Related Documents

- [SummaryCards.md](./SummaryCards.md) - Summary metrics
- [ToolStatsTable.md](./ToolStatsTable.md) - Detailed stats table
- [dashboard-page.md](../pages/dashboard-page.md) - Page using this component
- [interfaces.md](../../types/interfaces.md) - Chart data types

