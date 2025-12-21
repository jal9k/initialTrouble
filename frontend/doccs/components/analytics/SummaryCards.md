# SummaryCards Component

This document specifies the SummaryCards component for displaying analytics summary metrics.

## File Location

```
frontend/
  components/
    analytics/
      SummaryCards.tsx
```

---

## Overview

The SummaryCards component displays:
- Total sessions count
- Resolution rate percentage
- Average time to resolution
- Total cost (LLM API costs)

---

## Props Interface

```typescript
interface SummaryCardsProps {
  /** Summary data to display */
  summary: SessionSummary
  
  /** Loading state */
  isLoading?: boolean
  
  /** Additional CSS classes */
  className?: string
}
```

---

## Component Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SummaryCards                                                           │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐│
│  │ Total Sessions│ │Resolution Rate│ │ Avg Time      │ │ Total Cost    ││
│  │               │ │               │ │               │ │               ││
│  │     147       │ │    78.2%      │ │   4m 32s      │ │   $12.45      ││
│  │               │ │               │ │               │ │               ││
│  │ ↑ 12% vs last │ │ ↑ 5% vs last  │ │ ↓ 15% faster  │ │ ↓ 8% less     ││
│  └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component States

| State | Description | Visual |
|-------|-------------|--------|
| Loading | Data fetching | Skeleton cards |
| Default | Data loaded | Metric values |
| Empty | No data | Zero values or message |

---

## Behaviors

### Metric Display
- Large, prominent numbers
- Appropriate formatting per metric type
- Trend indicators (up/down arrows)

### Responsive Layout
- 4 columns on desktop
- 2 columns on tablet
- 1 column on mobile

---

## shadcn/ui Dependencies

| Component | Usage |
|-----------|-------|
| `Card` | Metric containers |
| `Skeleton` | Loading state |

---

## Styling Guidelines

### Card Grid
```css
.summary-grid {
  @apply grid gap-4;
  @apply grid-cols-1 sm:grid-cols-2 lg:grid-cols-4;
}
```

### Metric Card
```css
.metric-card {
  @apply p-6;
}

.metric-label {
  @apply text-sm font-medium text-muted-foreground;
}

.metric-value {
  @apply text-3xl font-bold tracking-tight;
}

.metric-trend {
  @apply text-xs flex items-center gap-1 mt-1;
}

.trend-up {
  @apply text-green-600 dark:text-green-400;
}

.trend-down {
  @apply text-red-600 dark:text-red-400;
}
```

---

## Implementation

```typescript
'use client'

import { cn, formatNumber, formatDuration } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { TrendingUp, TrendingDown, Activity, Clock, DollarSign, CheckCircle } from 'lucide-react'
import type { SessionSummary } from '@/types'

interface MetricCardProps {
  title: string
  value: string
  description?: string
  icon: typeof Activity
  trend?: {
    value: number
    isPositive: boolean
  }
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
    <div className={cn(
      'grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
      className
    )}>
      {metrics.map((metric) => (
        <MetricCard
          key={metric.title}
          {...metric}
          isLoading={isLoading}
        />
      ))}
    </div>
  )
}
```

---

## Accessibility

| Feature | Implementation |
|---------|---------------|
| Semantic HTML | Proper heading levels |
| Screen reader | Metric values announced |
| Color contrast | Trend colors meet WCAG |
| Reduced motion | Respects prefers-reduced-motion |

---

## Test Specifications

### Render Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| All cards rendered | 4 cards displayed |
| Values formatted | Correct format per type |
| Icons displayed | Each card has icon |
| Loading shows skeleton | Skeleton cards when loading |

### Format Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Session count formatted | Comma separators |
| Rate as percentage | Shows % symbol |
| Duration formatted | Human readable time |
| Cost as currency | $ symbol and cents |

### Responsive Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Desktop layout | 4 columns |
| Tablet layout | 2 columns |
| Mobile layout | 1 column |

---

## Lint/Build Verification

- [ ] Component properly typed
- [ ] All metrics formatted
- [ ] Responsive layout works
- [ ] Loading state works
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All tests pass

---

## Related Documents

- [SessionsChart.md](./SessionsChart.md) - Time series chart
- [ToolStatsTable.md](./ToolStatsTable.md) - Tool statistics
- [dashboard-page.md](../pages/dashboard-page.md) - Page using this component
- [interfaces.md](../../types/interfaces.md) - SessionSummary type

