'use client'

import { useState, useEffect, useMemo } from 'react'
import { SummaryCards } from '@/components/analytics/SummaryCards'
import { SessionsOverTimeChart, CategoryChart, ToolUsageChart } from '@/components/analytics/SessionsChart'
import { ToolStatsTable } from '@/components/analytics/ToolStatsTable'
import { DateRangePicker } from '@/components/analytics/DateRangePicker'
import type { SessionSummary, TimeSeriesPoint, CategoryBreakdown, ToolStats } from '@/types'

// Mock data - would come from API
const mockSummary: SessionSummary = {
  totalSessions: 147,
  resolvedCount: 115,
  unresolvedCount: 22,
  abandonedCount: 10,
  resolutionRate: 0.782,
  averageTimeToResolution: 272000, // 4m 32s in ms
  totalCost: 12.45
}

const mockCategoryData: CategoryBreakdown[] = [
  { category: 'connectivity', count: 45, percentage: 30.6 },
  { category: 'dns', count: 38, percentage: 25.9 },
  { category: 'wifi', count: 32, percentage: 21.8 },
  { category: 'ip_config', count: 20, percentage: 13.6 },
  { category: 'unknown', count: 12, percentage: 8.2 }
]

const mockToolUsage = [
  { name: 'ping_gateway', count: 89 },
  { name: 'test_dns_resolution', count: 76 },
  { name: 'get_ip_config', count: 65 },
  { name: 'check_adapter_status', count: 54 },
  { name: 'ping_dns', count: 43 }
]

function createMockToolStats(): ToolStats[] {
  const now = Date.now()
  return [
    {
      toolName: 'ping_gateway',
      executionCount: 89,
      successRate: 0.92,
      averageDuration: 245,
      lastUsed: new Date(now - 1000 * 60 * 5)
    },
    {
      toolName: 'test_dns_resolution',
      executionCount: 76,
      successRate: 0.88,
      averageDuration: 512,
      lastUsed: new Date(now - 1000 * 60 * 15)
    },
    {
      toolName: 'get_ip_config',
      executionCount: 65,
      successRate: 0.98,
      averageDuration: 128,
      lastUsed: new Date(now - 1000 * 60 * 30)
    },
    {
      toolName: 'check_adapter_status',
      executionCount: 54,
      successRate: 0.95,
      averageDuration: 312,
      lastUsed: new Date(now - 1000 * 60 * 60)
    },
    {
      toolName: 'ping_dns',
      executionCount: 43,
      successRate: 0.85,
      averageDuration: 189,
      lastUsed: new Date(now - 1000 * 60 * 120)
    }
  ]
}

function createMockSessionsData(): TimeSeriesPoint[] {
  const now = Date.now()
  return Array.from({ length: 14 }, (_, i) => ({
    timestamp: new Date(now - (13 - i) * 24 * 60 * 60 * 1000),
    value: Math.floor(Math.random() * 20) + 5
  }))
}

interface DateRange {
  startDate: Date
  endDate: Date
}

function getInitialDateRange(): DateRange {
  const now = Date.now()
  return {
    startDate: new Date(now - 30 * 24 * 60 * 60 * 1000),
    endDate: new Date(now)
  }
}

export default function DashboardPage() {
  const [isLoading, setIsLoading] = useState(true)
  const [dateRange, setDateRange] = useState<DateRange>(getInitialDateRange)
  
  const mockSessionsData = useMemo(() => createMockSessionsData(), [])
  const mockToolStats = useMemo(() => createMockToolStats(), [])

  // Simulate loading
  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 500)
    return () => clearTimeout(timer)
  }, [dateRange])

  const handleDateRangeChange = (range: DateRange) => {
    setIsLoading(true)
    setDateRange(range)
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
        <DateRangePicker
          value={dateRange}
          onChange={handleDateRangeChange}
        />
      </div>

      {/* Summary Cards */}
      <SummaryCards
        summary={mockSummary}
        isLoading={isLoading}
      />

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        <SessionsOverTimeChart
          data={mockSessionsData}
          chartType="area"
          title="Sessions Over Time"
          isLoading={isLoading}
        />
        <CategoryChart
          data={mockCategoryData}
          title="Issue Categories"
          isLoading={isLoading}
        />
      </div>

      {/* Tool Usage and Stats */}
      <div className="grid gap-6 lg:grid-cols-2">
        <ToolUsageChart
          data={mockToolUsage}
          title="Tool Usage"
          isLoading={isLoading}
        />
        <ToolStatsTable
          stats={mockToolStats}
          title="Tool Statistics"
          isLoading={isLoading}
        />
      </div>
    </div>
  )
}
