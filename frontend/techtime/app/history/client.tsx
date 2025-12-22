'use client'

import { useState, useMemo } from 'react'
import { cn, formatDate } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Search, Filter, Clock, ArrowRight } from 'lucide-react'
import Link from 'next/link'
import type { SessionListItem, SessionOutcome, IssueCategory } from '@/types'

interface HistoryPageClientProps {
  sessions: SessionListItem[]
}

const outcomeBadgeStyles: Record<SessionOutcome, string> = {
  resolved: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  unresolved: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  abandoned: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
  in_progress: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
}

const categoryLabels: Record<IssueCategory, string> = {
  connectivity: 'Connectivity',
  dns: 'DNS',
  wifi: 'WiFi',
  ip_config: 'IP Configuration',
  gateway: 'Gateway',
  unknown: 'Unknown'
}

export function HistoryPageClient({ sessions }: HistoryPageClientProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [outcomeFilter, setOutcomeFilter] = useState<SessionOutcome | 'all'>('all')
  const [categoryFilter, setCategoryFilter] = useState<IssueCategory | 'all'>('all')

  const filteredSessions = useMemo(() => {
    return sessions.filter(session => {
      // Search filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase()
        if (!session.preview.toLowerCase().includes(query)) {
          return false
        }
      }

      // Outcome filter
      if (outcomeFilter !== 'all' && session.outcome !== outcomeFilter) {
        return false
      }

      // Category filter
      if (categoryFilter !== 'all' && session.issueCategory !== categoryFilter) {
        return false
      }

      return true
    })
  }, [sessions, searchQuery, outcomeFilter, categoryFilter])

  const clearFilters = () => {
    setSearchQuery('')
    setOutcomeFilter('all')
    setCategoryFilter('all')
  }

  const hasActiveFilters = searchQuery || outcomeFilter !== 'all' || categoryFilter !== 'all'

  return (
    <div className="container py-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Session History</h1>
        <p className="text-muted-foreground">
          Browse and search through past diagnostic sessions
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search sessions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select
              value={outcomeFilter}
              onValueChange={(value) => setOutcomeFilter(value as SessionOutcome | 'all')}
            >
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Outcome" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All outcomes</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
                <SelectItem value="unresolved">Unresolved</SelectItem>
                <SelectItem value="abandoned">Abandoned</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={categoryFilter}
              onValueChange={(value) => setCategoryFilter(value as IssueCategory | 'all')}
            >
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                <SelectItem value="connectivity">Connectivity</SelectItem>
                <SelectItem value="dns">DNS</SelectItem>
                <SelectItem value="wifi">WiFi</SelectItem>
                <SelectItem value="ip_config">IP Config</SelectItem>
                <SelectItem value="gateway">Gateway</SelectItem>
                <SelectItem value="unknown">Unknown</SelectItem>
              </SelectContent>
            </Select>
            {hasActiveFilters && (
              <Button variant="ghost" onClick={clearFilters}>
                Clear filters
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {filteredSessions.length} session{filteredSessions.length !== 1 ? 's' : ''} found
          </p>
        </div>

        {filteredSessions.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Filter className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="font-semibold mb-2">No sessions found</h3>
              <p className="text-sm text-muted-foreground mb-4">
                {hasActiveFilters
                  ? 'Try adjusting your filters'
                  : 'No diagnostic sessions have been recorded yet'}
              </p>
              {hasActiveFilters && (
                <Button variant="outline" onClick={clearFilters}>
                  Clear filters
                </Button>
              )}
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {filteredSessions.map((session) => (
              <Card key={session.id} className="hover:bg-muted/50 transition-colors">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge
                          variant="secondary"
                          className={cn('text-xs', outcomeBadgeStyles[session.outcome])}
                        >
                          {session.outcome.replace('_', ' ')}
                        </Badge>
                        {session.issueCategory && (
                          <Badge variant="outline" className="text-xs">
                            {categoryLabels[session.issueCategory]}
                          </Badge>
                        )}
                      </div>
                      <p className="font-medium truncate">{session.preview}</p>
                      <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDate(session.startTime, 'datetime')}
                        </span>
                      </div>
                    </div>
                    <Link href={`/chat?session=${session.id}`}>
                      <Button variant="ghost" size="sm">
                        View
                        <ArrowRight className="h-4 w-4 ml-1" />
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

