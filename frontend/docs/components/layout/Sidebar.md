# Sidebar Component

This document specifies the Sidebar component for the Network Diagnostics application.

## File Location

```
frontend/
  components/
    layout/
      Sidebar.tsx
```

---

## Overview

The Sidebar component provides:
- Session history list
- New chat button
- Session filtering
- Active session highlighting
- Collapsible on mobile

---

## Props Interface

```typescript
interface SidebarProps {
  /** List of sessions to display */
  sessions: SessionListItem[]
  
  /** Currently active session ID */
  activeSessionId?: string
  
  /** Callback when session is selected */
  onSessionSelect: (sessionId: string) => void
  
  /** Callback when new session is requested */
  onNewSession: () => void
  
  /** Whether sessions are loading */
  isLoading?: boolean
  
  /** Additional CSS classes */
  className?: string
}
```

---

## Component Structure

```
┌──────────────────────────────┐
│  Sidebar                     │
│  ┌────────────────────────┐  │
│  │  [+ New Chat]          │  │
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │  Search/Filter         │  │
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │  Session List          │  │
│  │  ┌──────────────────┐  │  │
│  │  │ Session Item     │  │  │
│  │  │ - Preview text   │  │  │
│  │  │ - Timestamp      │  │  │
│  │  │ - Status badge   │  │  │
│  │  └──────────────────┘  │  │
│  │  ┌──────────────────┐  │  │
│  │  │ Session Item     │  │  │
│  │  │ ...              │  │  │
│  │  └──────────────────┘  │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

---

## Component States

| State | Description | Visual |
|-------|-------------|--------|
| Default | Sessions loaded | List of session items |
| Loading | Fetching sessions | Skeleton loaders |
| Empty | No sessions | Empty state message |
| Collapsed | Mobile hidden | Sheet/drawer pattern |

---

## Behaviors

### Session Selection
- Clicking session loads that conversation
- Active session highlighted with accent color
- Smooth transition between sessions

### New Chat
- Button at top creates new session
- Clears current conversation
- Optionally animates new item into list

### Search/Filter
- Real-time filtering by preview text
- Filter by outcome (resolved/unresolved)
- Debounced for performance

### Scrolling
- Virtual scrolling for long lists
- Preserves scroll position

---

## shadcn/ui Dependencies

| Component | Usage |
|-----------|-------|
| `Button` | New chat action |
| `Input` | Search field |
| `ScrollArea` | Scrollable session list |
| `Badge` | Outcome status badges |
| `Skeleton` | Loading states |
| `Sheet` | Mobile drawer |

---

## Styling Guidelines

### Layout
```css
.sidebar {
  @apply w-64 border-r bg-muted/40;
  @apply flex flex-col h-full;
}

.sidebar-header {
  @apply p-4 border-b;
}

.sidebar-content {
  @apply flex-1 overflow-hidden;
}
```

### Session Item
```css
.session-item {
  @apply p-3 cursor-pointer transition-colors;
  @apply hover:bg-muted;
  @apply border-l-2 border-transparent;
}

.session-item-active {
  @apply bg-muted border-l-primary;
}

.session-preview {
  @apply text-sm text-muted-foreground truncate;
}

.session-timestamp {
  @apply text-xs text-muted-foreground;
}
```

### Outcome Badges
```css
.badge-resolved {
  @apply bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200;
}

.badge-unresolved {
  @apply bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200;
}

.badge-abandoned {
  @apply bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200;
}
```

---

## Implementation

```typescript
'use client'

import { useState, useMemo } from 'react'
import { cn, formatDate, truncate } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Plus, Search } from 'lucide-react'
import type { SessionListItem, SessionOutcome } from '@/types'

const outcomeBadgeStyles: Record<SessionOutcome, string> = {
  resolved: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  unresolved: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  abandoned: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
  in_progress: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
}

export function Sidebar({
  sessions,
  activeSessionId,
  onSessionSelect,
  onNewSession,
  isLoading = false,
  className
}: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState('')

  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessions
    const query = searchQuery.toLowerCase()
    return sessions.filter(s =>
      s.preview.toLowerCase().includes(query)
    )
  }, [sessions, searchQuery])

  return (
    <aside className={cn(
      'w-64 border-r bg-muted/40 flex flex-col h-full',
      className
    )}>
      {/* Header */}
      <div className="p-4 border-b space-y-3">
        <Button
          onClick={onNewSession}
          className="w-full"
          variant="default"
        >
          <Plus className="h-4 w-4 mr-2" />
          New Chat
        </Button>

        <div className="relative">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search sessions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8"
          />
        </div>
      </div>

      {/* Session List */}
      <ScrollArea className="flex-1">
        <div className="p-2">
          {isLoading ? (
            // Loading skeletons
            Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="p-3 space-y-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))
          ) : filteredSessions.length === 0 ? (
            // Empty state
            <div className="p-4 text-center text-muted-foreground text-sm">
              {searchQuery ? 'No sessions match your search' : 'No sessions yet'}
            </div>
          ) : (
            // Session items
            filteredSessions.map(session => (
              <button
                key={session.id}
                onClick={() => onSessionSelect(session.id)}
                className={cn(
                  'w-full text-left p-3 rounded-lg transition-colors',
                  'hover:bg-muted border-l-2',
                  activeSessionId === session.id
                    ? 'bg-muted border-l-primary'
                    : 'border-transparent'
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-muted-foreground">
                    {formatDate(session.startTime, 'relative')}
                  </span>
                  <Badge
                    variant="secondary"
                    className={cn('text-xs', outcomeBadgeStyles[session.outcome])}
                  >
                    {session.outcome}
                  </Badge>
                </div>
                <p className="text-sm truncate">
                  {truncate(session.preview, 50)}
                </p>
                {session.issueCategory && (
                  <span className="text-xs text-muted-foreground">
                    {session.issueCategory}
                  </span>
                )}
              </button>
            ))
          )}
        </div>
      </ScrollArea>
    </aside>
  )
}
```

---

## Mobile Behavior

On mobile, the sidebar becomes a sheet/drawer:

```typescript
'use client'

import { useState } from 'react'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Menu } from 'lucide-react'
import { Sidebar, SidebarProps } from './Sidebar'

export function MobileSidebar(props: SidebarProps) {
  const [open, setOpen] = useState(false)

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden">
          <Menu className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="p-0 w-72">
        <Sidebar
          {...props}
          onSessionSelect={(id) => {
            props.onSessionSelect(id)
            setOpen(false)
          }}
        />
      </SheetContent>
    </Sheet>
  )
}
```

---

## Accessibility

| Feature | Implementation |
|---------|---------------|
| Keyboard nav | Arrow keys navigate sessions |
| Screen reader | Session items have descriptive labels |
| Focus management | Focus moves to selected session |
| Landmarks | Sidebar uses `<aside>` element |

---

## Test Specifications

### Render Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Renders new chat button | Button visible |
| Renders search input | Input visible |
| Renders session list | Sessions displayed |
| Renders loading state | Skeletons when isLoading |
| Renders empty state | Message when no sessions |

### Interaction Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| New chat button calls onNewSession | Callback invoked |
| Session click calls onSessionSelect | Callback with session ID |
| Search filters sessions | Matching sessions shown |
| Active session highlighted | Different styling applied |

### Filter Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Search filters by preview | Matching sessions shown |
| Empty search shows all | All sessions displayed |
| No results shows message | Empty state message |

### Accessibility Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Keyboard navigation works | Tab/Enter selects sessions |
| Screen reader announces items | Proper labels |
| Focus visible | Focus rings on items |

---

## Lint/Build Verification

- [ ] Component properly typed
- [ ] All imports resolved
- [ ] Loading state works
- [ ] Empty state works
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All tests pass

---

## Related Documents

- [Header.md](./Header.md) - Header component
- [chat-page.md](../pages/chat-page.md) - Page using this sidebar
- [interfaces.md](../../types/interfaces.md) - SessionListItem type

