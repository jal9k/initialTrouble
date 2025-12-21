# ToolStatsTable Component

This document specifies the ToolStatsTable component for displaying tool performance statistics.

## File Location

```
frontend/
  components/
    analytics/
      ToolStatsTable.tsx
```

---

## Overview

The ToolStatsTable component displays:
- Tool execution counts
- Success rates
- Average durations
- Last used timestamps
- Sortable columns

---

## Props Interface

```typescript
interface ToolStatsTableProps {
  /** Tool statistics data */
  stats: ToolStats[]
  
  /** Column to sort by */
  sortBy?: keyof ToolStats
  
  /** Sort direction */
  sortOrder?: 'asc' | 'desc'
  
  /** Callback when sort changes */
  onSort?: (column: keyof ToolStats) => void
  
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
│  Tool Performance                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Tool Name       │ Executions │ Success Rate │ Avg Duration │ Last │  │
│  │─────────────────┼────────────┼──────────────┼──────────────┼──────│  │
│  │ ping_gateway    │    156     │    94.2%     │    235ms     │ 2h   │  │
│  │ test_dns        │    134     │    87.3%     │    1.2s      │ 5h   │  │
│  │ check_adapter   │    112     │    99.1%     │    89ms      │ 1d   │  │
│  │ get_ip_config   │     98     │    100%      │    45ms      │ 3h   │  │
│  │ ping_dns        │     67     │    92.5%     │    312ms     │ 12h  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component States

| State | Description | Visual |
|-------|-------------|--------|
| Loading | Data fetching | Skeleton rows |
| Default | Data loaded | Table with data |
| Empty | No data | Empty state message |
| Sorted | Column sorted | Sort indicator |

---

## Behaviors

### Sorting
- Click column header to sort
- Toggle asc/desc on repeated clicks
- Visual indicator on sorted column

### Data Formatting
- Success rate as percentage with color coding
- Duration in human-readable format
- Last used as relative time

### Success Rate Coloring
- Green: >= 90%
- Yellow: 70-89%
- Red: < 70%

---

## shadcn/ui Dependencies

| Component | Usage |
|-----------|-------|
| `Table` | Data table |
| `Card` | Container |
| `Badge` | Success rate indicator |
| `Skeleton` | Loading state |
| `Button` | Sort headers |

---

## Styling Guidelines

### Table Styling
```css
.stats-table {
  @apply w-full;
}

.stats-header {
  @apply bg-muted/50;
}

.stats-header-cell {
  @apply cursor-pointer select-none;
  @apply hover:bg-muted;
}

.sort-indicator {
  @apply ml-1 h-4 w-4;
}
```

### Success Rate Badge
```css
.success-high {
  @apply bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200;
}

.success-medium {
  @apply bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200;
}

.success-low {
  @apply bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200;
}
```

---

## Implementation

```typescript
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
  if (rate >= 0.9) return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
  if (rate >= 0.7) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
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

export function ToolStatsTable({
  stats,
  sortBy: externalSortBy,
  sortOrder: externalSortOrder,
  onSort,
  isLoading = false,
  className
}: ToolStatsTableProps) {
  // Internal sort state if not controlled
  const [internalSortBy, setInternalSortBy] = useState<SortableColumn>('executionCount')
  const [internalSortOrder, setInternalSortOrder] = useState<'asc' | 'desc'>('desc')

  const sortBy = externalSortBy ?? internalSortBy
  const sortOrder = externalSortOrder ?? internalSortOrder

  const handleSort = (column: SortableColumn) => {
    if (onSort) {
      onSort(column)
    } else {
      if (column === internalSortBy) {
        setInternalSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
      } else {
        setInternalSortBy(column)
        setInternalSortOrder('desc')
      }
    }
  }

  const sortedStats = useMemo(() => {
    if (!stats.length) return []
    
    return [...stats].sort((a, b) => {
      let aVal = a[sortBy]
      let bVal = b[sortBy]

      // Handle date comparison
      if (sortBy === 'lastUsed') {
        aVal = new Date(aVal as Date).getTime()
        bVal = new Date(bVal as Date).getTime()
      }

      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1
      return 0
    })
  }, [stats, sortBy, sortOrder])

  const SortIcon = ({ column }: { column: SortableColumn }) => {
    if (column !== sortBy) {
      return <ArrowUpDown className="ml-1 h-4 w-4 text-muted-foreground" />
    }
    return sortOrder === 'asc' 
      ? <ArrowUp className="ml-1 h-4 w-4" />
      : <ArrowDown className="ml-1 h-4 w-4" />
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
              {columns.map(col => (
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
              sortedStats.map(stat => (
                <TableRow key={stat.toolName}>
                  <TableCell className="font-mono text-sm">
                    {stat.toolName}
                  </TableCell>
                  <TableCell>
                    {formatNumber(stat.executionCount)}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="secondary"
                      className={cn('font-mono', getSuccessRateStyle(stat.successRate))}
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

## Accessibility

| Feature | Implementation |
|---------|---------------|
| Keyboard nav | Tab through sortable headers |
| ARIA sort | aria-sort on sorted column |
| Screen reader | Sort direction announced |
| Focus visible | Focus ring on headers |

---

## Test Specifications

### Render Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| All columns rendered | 5 columns displayed |
| All rows rendered | One row per tool |
| Loading shows skeleton | Skeleton rows |
| Empty shows message | "No data" message |

### Format Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Execution count formatted | Numbers with commas |
| Success rate as percentage | Shows % |
| Duration formatted | Human readable |
| Last used relative | "2h ago" format |

### Sort Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Click sorts column | Data reorders |
| Click again reverses | asc/desc toggles |
| Sort indicator shown | Arrow on active column |
| Controlled sort works | External state used |

### Success Rate Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| >= 90% shows green | Green badge |
| 70-89% shows yellow | Yellow badge |
| < 70% shows red | Red badge |

---

## Lint/Build Verification

- [ ] Component properly typed
- [ ] Sort logic works
- [ ] Formatting correct
- [ ] Loading state works
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All tests pass

---

## Related Documents

- [SummaryCards.md](./SummaryCards.md) - Summary metrics
- [SessionsChart.md](./SessionsChart.md) - Chart visualizations
- [dashboard-page.md](../pages/dashboard-page.md) - Page using this component
- [interfaces.md](../../types/interfaces.md) - ToolStats type

