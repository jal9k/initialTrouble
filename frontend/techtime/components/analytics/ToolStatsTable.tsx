'use client'

import { useState, useMemo } from 'react'
import { formatDate, formatNumber, formatDuration } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { ToolStats, ToolStatsTableProps } from '@/types'

type SortKey = keyof ToolStats
type SortOrder = 'asc' | 'desc'

interface ExtendedToolStatsTableProps extends ToolStatsTableProps {
  title?: string
  isLoading?: boolean
  className?: string
}

export function ToolStatsTable({
  stats,
  sortBy: externalSortBy,
  sortOrder: externalSortOrder,
  onSort,
  title = 'Tool Statistics',
  isLoading = false,
  className
}: ExtendedToolStatsTableProps) {
  // Internal state for sorting if not controlled externally
  const [internalSortBy, setInternalSortBy] = useState<SortKey>('executionCount')
  const [internalSortOrder, setInternalSortOrder] = useState<SortOrder>('desc')

  const sortBy = externalSortBy || internalSortBy
  const sortOrder = externalSortOrder || internalSortOrder

  const handleSort = (column: SortKey) => {
    if (onSort) {
      onSort(column)
    } else {
      if (sortBy === column) {
        setInternalSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
      } else {
        setInternalSortBy(column)
        setInternalSortOrder('desc')
      }
    }
  }

  const sortedStats = useMemo(() => {
    return [...stats].sort((a, b) => {
      const aVal = a[sortBy]
      const bVal = b[sortBy]

      if (aVal instanceof Date && bVal instanceof Date) {
        return sortOrder === 'asc'
          ? aVal.getTime() - bVal.getTime()
          : bVal.getTime() - aVal.getTime()
      }

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortOrder === 'asc' ? aVal - bVal : bVal - aVal
      }

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortOrder === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal)
      }

      return 0
    })
  }, [stats, sortBy, sortOrder])

  const getSortIcon = (column: SortKey) => {
    if (sortBy !== column) {
      return <ArrowUpDown className="h-4 w-4" />
    }
    return sortOrder === 'asc'
      ? <ArrowUp className="h-4 w-4" />
      : <ArrowDown className="h-4 w-4" />
  }

  const getSuccessRateBadge = (rate: number) => {
    if (rate >= 0.9) {
      return <Badge variant="default" className="bg-green-500">High</Badge>
    }
    if (rate >= 0.7) {
      return <Badge variant="secondary">Medium</Badge>
    }
    return <Badge variant="destructive">Low</Badge>
  }

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <Skeleton className="h-5 w-32" />
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

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>
                <Button
                  variant="ghost"
                  size="sm"
                  className="-ml-3 h-8"
                  onClick={() => handleSort('toolName')}
                >
                  Tool Name
                  {getSortIcon('toolName')}
                </Button>
              </TableHead>
              <TableHead className="text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  className="-mr-3 h-8"
                  onClick={() => handleSort('executionCount')}
                >
                  Executions
                  {getSortIcon('executionCount')}
                </Button>
              </TableHead>
              <TableHead className="text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  className="-mr-3 h-8"
                  onClick={() => handleSort('successRate')}
                >
                  Success Rate
                  {getSortIcon('successRate')}
                </Button>
              </TableHead>
              <TableHead className="text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  className="-mr-3 h-8"
                  onClick={() => handleSort('averageDuration')}
                >
                  Avg Duration
                  {getSortIcon('averageDuration')}
                </Button>
              </TableHead>
              <TableHead className="text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  className="-mr-3 h-8"
                  onClick={() => handleSort('lastUsed')}
                >
                  Last Used
                  {getSortIcon('lastUsed')}
                </Button>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedStats.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  No tool statistics available
                </TableCell>
              </TableRow>
            ) : (
              sortedStats.map((stat) => (
                <TableRow key={stat.toolName}>
                  <TableCell className="font-mono text-sm">
                    {stat.toolName}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatNumber(stat.executionCount)}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      {formatNumber(stat.successRate, 'percent')}
                      {getSuccessRateBadge(stat.successRate)}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    {formatDuration(stat.averageDuration)}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
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

