# History Page

This document specifies the History page (`/history`), the session history browser.

## File Location

```
frontend/
  app/
    history/
      page.tsx
```

---

## Overview

The History page provides:
- Paginated list of past sessions
- Outcome and category filtering
- Search functionality
- Session details view
- Replay/continue conversation

---

## Page Structure

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Header                                                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  Session History                                                        │   │
│  │  ┌────────────────────┐ ┌────────────────┐ ┌────────────────┐          │   │
│  │  │ Search...          │ │ Outcome ▼      │ │ Category ▼     │          │   │
│  │  └────────────────────┘ └────────────────┘ └────────────────┘          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │   │
│  │  │  Session #1                                       Dec 21, 2:30 PM │  │   │
│  │  │  "My WiFi keeps disconnecting every few minutes"                  │  │   │
│  │  │  [Resolved] [WiFi] [5 messages] [2 tools used]      [Continue →] │  │   │
│  │  └───────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                          │   │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │   │
│  │  │  Session #2                                       Dec 20, 4:15 PM │  │   │
│  │  │  "I can't access any websites"                                    │  │   │
│  │  │  [Unresolved] [DNS] [8 messages] [4 tools used]     [Continue →] │  │   │
│  │  └───────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                          │   │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │   │
│  │  │  Session #3                                       Dec 19, 9:00 AM │  │   │
│  │  │  "Network is very slow today"                                     │  │   │
│  │  │  [Abandoned] [Connectivity] [3 messages] [1 tool]   [Continue →] │  │   │
│  │  └───────────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  [← Previous]         Page 1 of 10          [Next →]                   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Responsive Behavior

| Breakpoint | Layout |
|------------|--------|
| Desktop (lg+) | Full session cards with all badges |
| Tablet (md) | Condensed cards |
| Mobile (sm) | Stacked badges, compact layout |

---

## Data Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          History Page                                     │
│                                                                          │
│  URL State (nuqs)                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  ?page=1&outcome=resolved&category=dns&search=wifi                  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                               │                                          │
│                               ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    Server Component                                  │ │
│  │                                                                      │ │
│  │  const sessions = await listSessions({                              │ │
│  │    page, outcome, category, search                                  │ │
│  │  })                                                                 │ │
│  │                                                                      │ │
│  └────────────────────────────┬────────────────────────────────────────┘ │
│                               │                                          │
│                               ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    SessionList Component                             │ │
│  │                                                                      │ │
│  │  - SessionCard for each session                                     │ │
│  │  - Pagination controls                                              │ │
│  │  - Filter controls (client-side)                                    │ │
│  │                                                                      │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation

```typescript
// app/history/page.tsx

import { Suspense } from 'react'
import { listSessions } from '@/lib/api'
import { HistoryClient } from './client'
import { Skeleton } from '@/components/ui/skeleton'

export const metadata = {
  title: 'History - TechTime',
  description: 'Browse past diagnostic sessions'
}

interface SearchParams {
  page?: string
  outcome?: string
  category?: string
  search?: string
}

async function SessionList({ searchParams }: { searchParams: SearchParams }) {
  const sessions = await listSessions({
    page: parseInt(searchParams.page || '1'),
    pageSize: 10,
    outcome: searchParams.outcome as any,
    // Additional filters...
  })

  return (
    <HistoryClient
      initialSessions={sessions.items}
      total={sessions.total}
      page={sessions.page}
      pageSize={sessions.pageSize}
      hasMore={sessions.hasMore}
    />
  )
}

export default function HistoryPage({
  searchParams
}: {
  searchParams: SearchParams
}) {
  return (
    <div className="container py-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Session History</h1>
        <p className="text-muted-foreground">
          Browse and continue past diagnostic sessions
        </p>
      </div>

      <Suspense fallback={<HistoryLoading />}>
        <SessionList searchParams={searchParams} />
      </Suspense>
    </div>
  )
}

function HistoryLoading() {
  return (
    <div className="space-y-4">
      {/* Filters skeleton */}
      <div className="flex gap-4 mb-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-10 w-32" />
        <Skeleton className="h-10 w-32" />
      </div>
      
      {/* Session cards skeleton */}
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-32 w-full" />
      ))}
    </div>
  )
}
```

```typescript
// app/history/client.tsx
'use client'

import { useState, useCallback } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useQueryState } from 'nuqs'
import { cn, formatDate, truncate } from '@/lib/utils'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Search, ChevronLeft, ChevronRight, ArrowRight } from 'lucide-react'
import Link from 'next/link'
import type { SessionListItem, SessionOutcome, IssueCategory } from '@/types'

const outcomeBadgeStyles: Record<SessionOutcome, string> = {
  resolved: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  unresolved: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  abandoned: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
  in_progress: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
}

interface HistoryClientProps {
  initialSessions: SessionListItem[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}

export function HistoryClient({
  initialSessions,
  total,
  page,
  pageSize,
  hasMore
}: HistoryClientProps) {
  const router = useRouter()
  const [search, setSearch] = useQueryState('search')
  const [outcome, setOutcome] = useQueryState('outcome')
  const [category, setCategory] = useQueryState('category')
  const [pageNum, setPageNum] = useQueryState('page')

  const totalPages = Math.ceil(total / pageSize)

  const handleSearch = (value: string) => {
    setSearch(value || null)
    setPageNum('1')
  }

  const handleOutcomeChange = (value: string) => {
    setOutcome(value === 'all' ? null : value)
    setPageNum('1')
  }

  const handleCategoryChange = (value: string) => {
    setCategory(value === 'all' ? null : value)
    setPageNum('1')
  }

  const handlePageChange = (newPage: number) => {
    setPageNum(String(newPage))
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search sessions..."
            value={search || ''}
            onChange={(e) => handleSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        <Select
          value={outcome || 'all'}
          onValueChange={handleOutcomeChange}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Outcome" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Outcomes</SelectItem>
            <SelectItem value="resolved">Resolved</SelectItem>
            <SelectItem value="unresolved">Unresolved</SelectItem>
            <SelectItem value="abandoned">Abandoned</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={category || 'all'}
          onValueChange={handleCategoryChange}
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            <SelectItem value="connectivity">Connectivity</SelectItem>
            <SelectItem value="dns">DNS</SelectItem>
            <SelectItem value="wifi">WiFi</SelectItem>
            <SelectItem value="ip_config">IP Config</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Session List */}
      <div className="space-y-4">
        {initialSessions.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              No sessions found matching your criteria
            </CardContent>
          </Card>
        ) : (
          initialSessions.map(session => (
            <SessionCard key={session.id} session={session} />
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={() => handlePageChange(page - 1)}
            disabled={page <= 1}
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            Previous
          </Button>

          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>

          <Button
            variant="outline"
            onClick={() => handlePageChange(page + 1)}
            disabled={!hasMore}
          >
            Next
            <ChevronRight className="h-4 w-4 ml-2" />
          </Button>
        </div>
      )}
    </div>
  )
}

function SessionCard({ session }: { session: SessionListItem }) {
  return (
    <Card className="hover:border-primary/50 transition-colors">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm text-muted-foreground">
                {formatDate(session.startTime, 'datetime')}
              </span>
            </div>

            {/* Preview */}
            <p className="text-sm mb-3">
              "{truncate(session.preview, 100)}"
            </p>

            {/* Badges */}
            <div className="flex flex-wrap gap-2">
              <Badge
                variant="secondary"
                className={outcomeBadgeStyles[session.outcome]}
              >
                {session.outcome}
              </Badge>
              
              {session.issueCategory && (
                <Badge variant="outline">
                  {session.issueCategory}
                </Badge>
              )}
            </div>
          </div>

          {/* Continue button */}
          <Link href={`/chat?session=${session.id}`}>
            <Button variant="ghost" size="sm">
              Continue
              <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}
```

---

## URL State

The page uses URL state for all filters:

```
/history?page=2&outcome=resolved&category=dns&search=wifi
```

This enables:
- Shareable filtered views
- Back/forward navigation
- Bookmarkable searches

---

## Loading State

```typescript
// app/history/loading.tsx
import { Skeleton } from '@/components/ui/skeleton'

export default function HistoryLoading() {
  return (
    <div className="container py-6">
      <div className="mb-6">
        <Skeleton className="h-9 w-48 mb-2" />
        <Skeleton className="h-4 w-64" />
      </div>

      <div className="flex gap-4 mb-6">
        <Skeleton className="h-10 flex-1" />
        <Skeleton className="h-10 w-40" />
        <Skeleton className="h-10 w-40" />
      </div>

      <div className="space-y-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-32 w-full" />
        ))}
      </div>

      <div className="flex justify-between mt-6">
        <Skeleton className="h-10 w-24" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-10 w-24" />
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
| Page renders | Sessions list visible |
| Empty state shows | Message when no sessions |
| Pagination works | Page changes update list |

### Filter Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Search filters | Matching sessions shown |
| Outcome filter works | Only matching outcomes |
| Category filter works | Only matching categories |
| Filters combine | AND logic applied |
| URL updates | Filters in URL params |

### Interaction Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Continue navigates | Goes to /chat?session=id |
| Pagination buttons | Previous/next work |
| Filter clear | Resets to all |

### Responsive Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Mobile stacks filters | Vertical layout |
| Desktop shows row | Horizontal layout |

---

## Lint/Build Verification

- [ ] Page renders without errors
- [ ] URL state syncs correctly
- [ ] Pagination works
- [ ] Filters work
- [ ] Links navigate correctly
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All tests pass

---

## Related Documents

- [Sidebar.md](../layout/Sidebar.md) - Similar session list
- [chat-page.md](./chat-page.md) - Destination for continue
- [api.md](../../lib/api.md) - listSessions function
- [interfaces.md](../../types/interfaces.md) - SessionListItem type

