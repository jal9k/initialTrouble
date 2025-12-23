# Phase 4.1: Layout Components

Implementing Header, Sidebar, and MobileSidebar components.

---

## Prerequisites

- Phase 1-3 completed
- All shadcn/ui components installed
- `useWebSocket` hook working

---

## Step 1: Update Header Component

Update `components/layout/Header.tsx` with mobile menu:

```typescript
// components/layout/Header.tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import { Moon, Sun, Menu, Wifi, WifiOff } from 'lucide-react'
import { useTheme } from 'next-themes'
import { useWebSocket } from '@/hooks/use-websocket'

const navItems = [
  { href: '/chat', label: 'Chat' },
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/history', label: 'History' }
]

interface HeaderProps {
  className?: string
}

export function Header({ className }: HeaderProps) {
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const { isConnected, isConnecting } = useWebSocket()

  return (
    <header
      className={cn(
        'sticky top-0 z-50 w-full border-b',
        'bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60',
        className
      )}
    >
      <div className="container flex h-14 items-center">
        {/* Logo */}
        <Link href="/" className="mr-6 flex items-center space-x-2">
          <span className="font-bold">Network Diag</span>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex gap-6">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'text-sm font-medium transition-colors hover:text-primary',
                pathname === item.href ? 'text-primary' : 'text-muted-foreground'
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Actions */}
        <div className="flex items-center gap-2">
          {/* Connection Status */}
          <div className="flex items-center gap-1 text-sm">
            {isConnected ? (
              <Wifi className="h-4 w-4 text-green-500" />
            ) : isConnecting ? (
              <Wifi className="h-4 w-4 text-yellow-500 animate-pulse" />
            ) : (
              <WifiOff className="h-4 w-4 text-red-500" />
            )}
          </div>

          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            <span className="sr-only">Toggle theme</span>
          </Button>

          {/* Mobile Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild className="md:hidden">
              <Button variant="ghost" size="icon">
                <Menu className="h-4 w-4" />
                <span className="sr-only">Open menu</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {navItems.map((item) => (
                <DropdownMenuItem key={item.href} asChild>
                  <Link href={item.href}>{item.label}</Link>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}
```

---

## Step 2: Create Sidebar Component

Create `components/layout/Sidebar.tsx`:

```typescript
// components/layout/Sidebar.tsx
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

interface SidebarProps {
  sessions: SessionListItem[]
  activeSessionId?: string | null
  onSessionSelect: (sessionId: string) => void
  onNewSession: () => void
  isLoading?: boolean
  className?: string
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
    return sessions.filter((s) =>
      s.preview.toLowerCase().includes(query)
    )
  }, [sessions, searchQuery])

  return (
    <aside
      className={cn(
        'w-64 border-r bg-muted/40 flex flex-col h-full',
        className
      )}
    >
      {/* Header */}
      <div className="p-4 border-b space-y-3">
        <Button onClick={onNewSession} className="w-full" variant="default">
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
            filteredSessions.map((session) => (
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
                    {session.outcome.replace('_', ' ')}
                  </Badge>
                </div>
                <p className="text-sm truncate">
                  {truncate(session.preview, 50)}
                </p>
                {session.issueCategory && (
                  <span className="text-xs text-muted-foreground">
                    {session.issueCategory.replace('_', ' ')}
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

## Step 3: Create MobileSidebar Component

Create `components/layout/MobileSidebar.tsx`:

```typescript
// components/layout/MobileSidebar.tsx
'use client'

import { useState } from 'react'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Menu } from 'lucide-react'
import { Sidebar } from './Sidebar'
import type { SessionListItem } from '@/types'

interface MobileSidebarProps {
  sessions: SessionListItem[]
  activeSessionId?: string | null
  onSessionSelect: (sessionId: string) => void
  onNewSession: () => void
  isLoading?: boolean
}

export function MobileSidebar({
  sessions,
  activeSessionId,
  onSessionSelect,
  onNewSession,
  isLoading
}: MobileSidebarProps) {
  const [open, setOpen] = useState(false)

  const handleSessionSelect = (id: string) => {
    onSessionSelect(id)
    setOpen(false)
  }

  const handleNewSession = () => {
    onNewSession()
    setOpen(false)
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden">
          <Menu className="h-5 w-5" />
          <span className="sr-only">Open sessions</span>
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="p-0 w-72">
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSessionSelect={handleSessionSelect}
          onNewSession={handleNewSession}
          isLoading={isLoading}
          className="border-r-0"
        />
      </SheetContent>
    </Sheet>
  )
}
```

---

## Step 4: Create Layout Index Export

Create `components/layout/index.ts`:

```typescript
// components/layout/index.ts

export { Header } from './Header'
export { Sidebar } from './Sidebar'
export { MobileSidebar } from './MobileSidebar'
```

---

## Step 5: Verify Phase 4.1

```bash
# Type check
npx tsc --noEmit

# Lint
npm run lint

# Build
npm run build
```

---

## Phase 4.1 Checklist

- [ ] Header updated with mobile dropdown menu
- [ ] Header shows connection status (green/yellow/red)
- [ ] Sidebar component created with session list
- [ ] Sidebar search/filter works
- [ ] Sidebar shows loading skeletons
- [ ] Sidebar shows empty state
- [ ] MobileSidebar uses Sheet component
- [ ] MobileSidebar closes on selection
- [ ] All components properly typed
- [ ] `tsc --noEmit` passes
- [ ] `npm run lint` passes
- [ ] `npm run build` passes

**Gate: All checks must pass before proceeding to Phase 4.2**


