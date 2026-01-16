'use client'

import { useState, useEffect, useCallback } from 'react'
import { SummaryCards } from '@/components/analytics/SummaryCards'
import { SessionsOverTimeChart, CategoryChart, ToolUsageChart } from '@/components/analytics/SessionsChart'
import { ToolStatsTable } from '@/components/analytics/ToolStatsTable'
import { DateRangePicker } from '@/components/analytics/DateRangePicker'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { AlertCircle, RefreshCw } from 'lucide-react'
import {
  getAnalyticsSummary,
  getToolStats,
  getSessionsOverTime,
  getCategoryBreakdown
} from '@/lib/api'
import { DEFAULT_DATE_RANGE_MS } from '@/lib/constants'
import type { SessionSummary, TimeSeriesPoint, CategoryBreakdown, ToolStats } from '@/types'

interface DateRange {
  startDate: Date
  endDate: Date
}

function getInitialDateRange(): DateRange {
  const now = Date.now()
  return {
    startDate: new Date(now - DEFAULT_DATE_RANGE_MS),
    endDate: new Date(now)
  }
}

// Default empty states
const emptySummary: SessionSummary = {
  totalSessions: 0,
  resolvedCount: 0,
  unresolvedCount: 0,
  abandonedCount: 0,
  resolutionRate: 0,
  averageTimeToResolution: 0,
  totalCost: 0
}

export default function DashboardPage() {
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dateRange, setDateRange] = useState<DateRange>(getInitialDateRange)
  
  // Data state
  const [summary, setSummary] = useState<SessionSummary>(emptySummary)
  const [sessionsData, setSessionsData] = useState<TimeSeriesPoint[]>([])
  const [categoryData, setCategoryData] = useState<CategoryBreakdown[]>([])
  const [toolStats, setToolStats] = useState<ToolStats[]>([])

  // Fetch all dashboard data
  const fetchData = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      // Fetch all data in parallel
      const [summaryResult, sessionsResult, categoriesResult, toolsResult] = await Promise.all([
        getAnalyticsSummary({
          startDate: dateRange.startDate,
          endDate: dateRange.endDate
        }),
        getSessionsOverTime({
          startDate: dateRange.startDate,
          endDate: dateRange.endDate,
          granularity: 'day'
        }),
        getCategoryBreakdown(),
        getToolStats()
      ])
      
      setSummary(summaryResult)
      setSessionsData(sessionsResult)
      setCategoryData(categoriesResult)
      setToolStats(toolsResult)
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err)
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data')
    } finally {
      setIsLoading(false)
    }
  }, [dateRange])

  // Fetch data on mount and when date range changes
  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleDateRangeChange = (range: DateRange) => {
    setDateRange(range)
  }

  // Convert tool stats to tool usage format for the chart
  const toolUsageData = toolStats.map(stat => ({
    name: stat.toolName,
    count: stat.executionCount
  }))

  // Error state
  if (error && !isLoading) {
    return (
      <div className="container py-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground">
              Analytics and insights for your support sessions
            </p>
          </div>
        </div>
        
        <Card>
          <CardContent className="py-12 text-center">
            <AlertCircle className="h-12 w-12 mx-auto text-destructive mb-4" />
            <h3 className="font-semibold mb-2">Failed to load dashboard</h3>
            <p className="text-sm text-muted-foreground mb-4">{error}</p>
            <Button variant="outline" onClick={fetchData}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Try again
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Analytics and insights for your support sessions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchData}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-1 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <DateRangePicker
            value={dateRange}
            onChange={handleDateRangeChange}
          />
        </div>
      </div>

      {/* Summary Cards */}
      <SummaryCards
        summary={summary}
        isLoading={isLoading}
      />

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        <SessionsOverTimeChart
          data={sessionsData}
          chartType="area"
          title="Sessions Over Time"
          isLoading={isLoading}
        />
        <CategoryChart
          data={categoryData}
          title="Issue Categories"
          isLoading={isLoading}
        />
      </div>

      {/* Tool Usage and Stats */}
      <div className="grid gap-6 lg:grid-cols-2">
        <ToolUsageChart
          data={toolUsageData}
          title="Tool Usage"
          isLoading={isLoading}
        />
        <ToolStatsTable
          stats={toolStats}
          title="Tool Statistics"
          isLoading={isLoading}
        />
      </div>
    </div>
  )
}
