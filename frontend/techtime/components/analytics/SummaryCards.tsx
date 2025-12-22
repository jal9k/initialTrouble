'use client'

import { cn, formatNumber, formatDuration } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { TrendingUp, TrendingDown, Activity, Clock, DollarSign, CheckCircle } from 'lucide-react'
import type { SummaryCardsProps } from '@/types'

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

