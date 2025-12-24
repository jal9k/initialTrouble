# Phase 4: Components

Building all UI components from the documentation specs. This phase is organized into sub-phases based on component dependencies.

**Prerequisites:** Phases 1-3 completed with all checks passing.

---

## Overview

| Sub-Phase | Components | Complexity | Est. Time |
|-----------|------------|------------|-----------|
| 4.1 | Layout (Header enhancement, Sidebar) | Low | 30 min |
| 4.2 | Chat (MessageBubble, ToolExecutionCard, ChatWindow) | Medium | 45 min |
| 4.3 | Diagnostics (ToolCard, OSILadderViz, ManualToolPanel) | Medium | 45 min |
| 4.4 | Analytics (SummaryCards, SessionsChart, ToolStatsTable) | Medium | 45 min |
| 4.5 | Pages (Home, Chat, Dashboard, History) | High | 60 min |

**Total estimated time:** ~4 hours

---

## Dependency Graph

```
                    ┌─────────────────────────────────────────────────────────────────┐
                    │                          PAGES                                   │
                    │  ┌─────────┐  ┌───────────┐  ┌─────────────┐  ┌───────────────┐ │
                    │  │  Home   │  │   Chat    │  │  Dashboard  │  │    History    │ │
                    │  └─────────┘  └─────┬─────┘  └──────┬──────┘  └───────────────┘ │
                    └─────────────────────┼───────────────┼───────────────────────────┘
                                          │               │
                    ┌─────────────────────▼───────────────▼───────────────────────────┐
                    │                       COMPOSITE COMPONENTS                       │
                    │  ┌────────────┐  ┌───────────────┐  ┌─────────────────────────┐ │
                    │  │ ChatWindow │  │ ManualToolPanel│  │  Charts (Sessions,     │ │
                    │  │            │  │               │  │  Category, ToolUsage)  │ │
                    │  └─────┬──────┘  └───────┬───────┘  └─────────────────────────┘ │
                    └────────┼─────────────────┼──────────────────────────────────────┘
                             │                 │
                    ┌────────▼─────────────────▼──────────────────────────────────────┐
                    │                        LEAF COMPONENTS                           │
                    │  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
                    │  │MessageBubble│  │ToolExecutionCard │  │    ToolCard      │   │
                    │  └─────────────┘  └──────────────────┘  └──────────────────┘   │
                    │  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
                    │  │ OSILadderViz│  │   SummaryCards   │  │  ToolStatsTable  │   │
                    │  └─────────────┘  └──────────────────┘  └──────────────────┘   │
                    │  ┌─────────────┐  ┌──────────────────┐                         │
                    │  │   Sidebar   │  │   MobileSidebar  │                         │
                    │  └─────────────┘  └──────────────────┘                         │
                    └─────────────────────────────────────────────────────────────────┘
                                                 │
                    ┌────────────────────────────▼────────────────────────────────────┐
                    │                        FOUNDATION                                │
                    │  shadcn/ui components │ hooks │ lib/utils │ lib/api │ types    │
                    └─────────────────────────────────────────────────────────────────┘
```

---

## Sub-Phase 4.1: Layout Components

### Components to Build

| Component | File | Status |
|-----------|------|--------|
| Header (enhanced) | `components/layout/Header.tsx` | Exists, needs mobile menu |
| Sidebar | `components/layout/Sidebar.tsx` | New |
| MobileSidebar | `components/layout/MobileSidebar.tsx` | New |

### Step 4.1.1: Enhance Header with Mobile Menu

Update `components/layout/Header.tsx`:

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
import { Moon, Sun, Wifi, WifiOff, Menu } from 'lucide-react'
import { useTheme } from 'next-themes'
import { useWebSocket } from '@/hooks/use-websocket'
import type { HeaderProps } from '@/types'

const navItems = [
  { href: '/chat', label: 'Chat' },
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/history', label: 'History' }
]

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
          <span className="font-bold text-lg">TechTim(e)</span>
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
          <div
            className="flex items-center gap-1 text-sm"
            role="status"
            aria-label={
              isConnected
                ? 'Connected to server'
                : isConnecting
                ? 'Connecting to server'
                : 'Disconnected from server'
            }
          >
            {isConnected ? (
              <Wifi className="h-4 w-4 text-green-500" aria-hidden="true" />
            ) : isConnecting ? (
              <Wifi className="h-4 w-4 text-yellow-500 animate-pulse" aria-hidden="true" />
            ) : (
              <WifiOff className="h-4 w-4 text-red-500" aria-hidden="true" />
            )}
          </div>

          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          </Button>

          {/* Mobile Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild className="md:hidden">
              <Button variant="ghost" size="icon" aria-label="Open navigation menu">
                <Menu className="h-5 w-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              {navItems.map((item) => (
                <DropdownMenuItem key={item.href} asChild>
                  <Link
                    href={item.href}
                    className={cn(
                      pathname === item.href && 'font-semibold'
                    )}
                  >
                    {item.label}
                  </Link>
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

### Step 4.1.2: Create Sidebar Component

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
import type { SidebarProps, SessionOutcome } from '@/types'

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
    return sessions.filter((s) => s.preview.toLowerCase().includes(query))
  }, [sessions, searchQuery])

  return (
    <aside
      className={cn('w-64 border-r bg-muted/40 flex flex-col h-full', className)}
      role="complementary"
      aria-label="Session history"
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
            aria-label="Search sessions"
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
                  'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
                  activeSessionId === session.id
                    ? 'bg-muted border-l-primary'
                    : 'border-transparent'
                )}
                aria-current={activeSessionId === session.id ? 'true' : undefined}
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
                <p className="text-sm truncate">{truncate(session.preview, 50)}</p>
                {session.issueCategory && (
                  <span className="text-xs text-muted-foreground capitalize">
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

### Step 4.1.3: Create MobileSidebar Component

Create `components/layout/MobileSidebar.tsx`:

```typescript
// components/layout/MobileSidebar.tsx
'use client'

import { useState } from 'react'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Menu } from 'lucide-react'
import { Sidebar } from './Sidebar'
import type { SidebarProps } from '@/types'

export function MobileSidebar(props: SidebarProps) {
  const [open, setOpen] = useState(false)

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open session sidebar">
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
          onNewSession={() => {
            props.onNewSession()
            setOpen(false)
          }}
        />
      </SheetContent>
    </Sheet>
  )
}
```

---

### Step 4.1.4: Create Layout Index Export

Create `components/layout/index.ts`:

```typescript
// components/layout/index.ts
export { Header } from './Header'
export { Sidebar } from './Sidebar'
export { MobileSidebar } from './MobileSidebar'
```

---

### Verification 4.1

```bash
# Type check
npx tsc --noEmit

# Lint
npm run lint

# Build
npm run build
```

**Checklist:**
- [ ] Header has mobile menu dropdown
- [ ] Sidebar renders with session list
- [ ] MobileSidebar opens as sheet on mobile
- [ ] All accessibility attributes present
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] Build passes

---

## Sub-Phase 4.2: Chat Components

### Components to Build

| Component | File | Status |
|-----------|------|--------|
| MessageBubble | `components/chat/MessageBubble.tsx` | New |
| ToolExecutionCard | `components/chat/ToolExecutionCard.tsx` | New |
| ChatWindow | `components/chat/ChatWindow.tsx` | New |

### Step 4.2.1: Install Markdown Dependencies

```bash
npm install react-markdown remark-gfm
```

---

### Step 4.2.2: Create MessageBubble Component

Create `components/chat/MessageBubble.tsx`:

```typescript
// components/chat/MessageBubble.tsx
'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn, formatDate } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Check, Copy, Zap } from 'lucide-react'
import type { MessageBubbleProps, MessageRole } from '@/types'

const roleStyles: Record<MessageRole, string> = {
  user: 'ml-auto bg-primary text-primary-foreground rounded-2xl rounded-br-md',
  assistant: 'mr-auto bg-muted rounded-2xl rounded-bl-md',
  system: 'mx-auto text-muted-foreground text-sm text-center italic max-w-[90%]',
  tool: 'mr-auto bg-muted/50 border rounded-lg font-mono text-sm'
}

export function MessageBubble({
  message,
  isLatest = false,
  showTimestamp = true,
  className
}: MessageBubbleProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const showCopyButton = message.role === 'assistant'
  const shouldRenderMarkdown = message.role === 'assistant'

  return (
    <div
      className={cn(
        'group flex flex-col',
        message.role === 'user' ? 'items-end' : 'items-start',
        isLatest && 'animate-in fade-in slide-in-from-bottom-2 duration-200',
        className
      )}
    >
      {/* Tool indicator */}
      {message.role === 'tool' && message.toolResult && (
        <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
          <Zap className="h-3 w-3" />
          <span>{message.toolResult.name}</span>
        </div>
      )}

      {/* Message bubble */}
      <div
        className={cn('px-4 py-2 max-w-[80%]', roleStyles[message.role])}
      >
        {shouldRenderMarkdown ? (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            className="prose prose-sm dark:prose-invert max-w-none"
            components={{
              a: ({ href, children }) => (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary underline"
                >
                  {children}
                </a>
              ),
              code: ({ inline, className: codeClassName, children }) => {
                if (inline) {
                  return (
                    <code className="bg-muted px-1 py-0.5 rounded text-sm">
                      {children}
                    </code>
                  )
                }
                return (
                  <pre className="bg-muted rounded-md p-3 overflow-x-auto">
                    <code className={codeClassName}>{children}</code>
                  </pre>
                )
              }
            }}
          >
            {message.content}
          </ReactMarkdown>
        ) : (
          <p className="whitespace-pre-wrap">{message.content}</p>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center gap-2 mt-1 px-1">
        {showTimestamp && (
          <span className="text-xs text-muted-foreground">
            {formatDate(message.timestamp, 'time')}
          </span>
        )}

        {showCopyButton && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={handleCopy}
                aria-label={copied ? 'Copied' : 'Copy message'}
              >
                {copied ? (
                  <Check className="h-3 w-3 text-green-500" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{copied ? 'Copied!' : 'Copy message'}</TooltipContent>
          </Tooltip>
        )}
      </div>

      {/* Tool calls indicator */}
      {message.toolCalls && message.toolCalls.length > 0 && (
        <div className="mt-2 text-xs text-muted-foreground">
          Used: {message.toolCalls.map((tc) => tc.name).join(', ')}
        </div>
      )}
    </div>
  )
}
```

---

### Step 4.2.3: Create ToolExecutionCard Component

Create `components/chat/ToolExecutionCard.tsx`:

```typescript
// components/chat/ToolExecutionCard.tsx
'use client'

import { useState } from 'react'
import { cn, formatDuration } from '@/lib/utils'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger
} from '@/components/ui/collapsible'
import { Loader2, Check, X, ChevronDown, Copy } from 'lucide-react'
import type { ToolExecutionCardProps, ToolExecutionStatus } from '@/types'

const statusConfig: Record<
  ToolExecutionStatus,
  {
    icon: typeof Loader2 | null
    color: string
    bg: string
    label: string
  }
> = {
  idle: {
    icon: null,
    color: 'border-muted',
    bg: 'bg-muted/50',
    label: 'Idle'
  },
  executing: {
    icon: Loader2,
    color: 'border-blue-500/50',
    bg: 'bg-blue-50 dark:bg-blue-950/20',
    label: 'Executing'
  },
  success: {
    icon: Check,
    color: 'border-green-500/50',
    bg: 'bg-green-50 dark:bg-green-950/20',
    label: 'Success'
  },
  error: {
    icon: X,
    color: 'border-red-500/50',
    bg: 'bg-red-50 dark:bg-red-950/20',
    label: 'Error'
  }
}

export function ToolExecutionCard({
  execution,
  onCancel,
  showDetails = false,
  className
}: ToolExecutionCardProps) {
  const [isOpen, setIsOpen] = useState(showDetails)
  const [copied, setCopied] = useState(false)

  const config = statusConfig[execution.status]
  const Icon = config.icon
  const duration =
    execution.startTime && execution.endTime
      ? execution.endTime.getTime() - execution.startTime.getTime()
      : null

  if (execution.status === 'idle') {
    return null
  }

  const handleCopy = async () => {
    const content =
      typeof execution.result === 'object'
        ? JSON.stringify(execution.result, null, 2)
        : String(execution.result)
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Card
      className={cn(
        'border transition-colors',
        config.color,
        config.bg,
        'animate-in fade-in slide-in-from-left-2 duration-200',
        className
      )}
      role="status"
      aria-label={`Tool ${execution.toolName} is ${config.label.toLowerCase()}`}
    >
      <CardHeader className="py-3 px-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {Icon && (
              <Icon
                className={cn(
                  'h-4 w-4',
                  execution.status === 'executing' && 'animate-spin',
                  execution.status === 'success' && 'text-green-600',
                  execution.status === 'error' && 'text-red-600'
                )}
                aria-hidden="true"
              />
            )}
            <span className="font-mono text-sm font-medium">
              {execution.toolName}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {duration && (
              <Badge variant="secondary" className="text-xs">
                {formatDuration(duration)}
              </Badge>
            )}

            {execution.status === 'executing' && onCancel && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onCancel}
                className="h-6 text-xs"
              >
                Cancel
              </Button>
            )}
          </div>
        </div>

        {/* Progress bar for executing state */}
        {execution.status === 'executing' && (
          <div className="mt-2 h-1 w-full bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary"
              style={{
                width: '100%',
                animation: 'shimmer 1.5s infinite'
              }}
            />
          </div>
        )}
      </CardHeader>

      {/* Result/Error content */}
      {(execution.result || execution.error) && (
        <Collapsible open={isOpen} onOpenChange={setIsOpen}>
          <CardContent className="pt-0 px-4 pb-3">
            {execution.error ? (
              <div className="text-sm text-red-600 dark:text-red-400">
                {execution.error}
              </div>
            ) : (
              <>
                <CollapsibleTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full justify-between h-8"
                  >
                    <span className="text-xs text-muted-foreground">
                      {isOpen ? 'Hide details' : 'Show details'}
                    </span>
                    <ChevronDown
                      className={cn(
                        'h-4 w-4 transition-transform',
                        isOpen && 'rotate-180'
                      )}
                    />
                  </Button>
                </CollapsibleTrigger>

                <CollapsibleContent>
                  <div className="relative mt-2">
                    <pre className="font-mono text-xs bg-muted rounded p-3 overflow-x-auto max-h-48 overflow-y-auto">
                      {typeof execution.result === 'object'
                        ? JSON.stringify(execution.result, null, 2)
                        : String(execution.result)}
                    </pre>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute top-1 right-1 h-6 w-6"
                      onClick={handleCopy}
                      aria-label="Copy result"
                    >
                      {copied ? (
                        <Check className="h-3 w-3 text-green-500" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                </CollapsibleContent>
              </>
            )}
          </CardContent>
        </Collapsible>
      )}
    </Card>
  )
}
```

---

### Step 4.2.4: Create ChatWindow Component

Create `components/chat/ChatWindow.tsx`:

```typescript
// components/chat/ChatWindow.tsx
'use client'

import { useRef, useEffect, useState, useCallback } from 'react'
import { useChat, UseChatOptions } from '@/hooks/use-chat'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent } from '@/components/ui/card'
import { MessageBubble } from './MessageBubble'
import { ToolExecutionCard } from './ToolExecutionCard'
import { Send, ArrowDown, RefreshCw } from 'lucide-react'
import type { ChatWindowProps } from '@/types'

const SUGGESTIONS = [
  'My WiFi keeps disconnecting',
  "I can't access the internet",
  'DNS resolution is failing',
  'Slow network speeds'
]

interface ExtendedChatWindowProps extends ChatWindowProps, UseChatOptions {}

export function ChatWindow({
  className,
  initialConversationId,
  onSessionStart,
  onSessionEnd,
  ...chatOptions
}: ExtendedChatWindowProps) {
  const {
    messages,
    isStreaming,
    isEmpty,
    error,
    currentToolExecution,
    sendMessage,
    retryLastMessage
  } = useChat({
    initialConversationId,
    onSessionStart,
    onSessionEnd,
    ...chatOptions
  })

  const [input, setInput] = useState('')
  const [showScrollButton, setShowScrollButton] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector(
        '[data-radix-scroll-area-viewport]'
      )
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }, [messages, currentToolExecution])

  // Handle scroll position for "scroll to bottom" button
  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    const target = event.target as HTMLDivElement
    const isNearBottom =
      target.scrollHeight - target.scrollTop - target.clientHeight < 100
    setShowScrollButton(!isNearBottom)
  }, [])

  // Scroll to bottom handler
  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector(
        '[data-radix-scroll-area-viewport]'
      )
      if (scrollContainer) {
        scrollContainer.scrollTo({
          top: scrollContainer.scrollHeight,
          behavior: 'smooth'
        })
      }
    }
  }

  // Handle send
  const handleSend = async () => {
    if (!input.trim() || isStreaming) return
    const message = input.trim()
    setInput('')
    await sendMessage(message)
  }

  // Handle key down
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Handle suggestion click
  const handleSuggestionClick = (suggestion: string) => {
    sendMessage(suggestion)
  }

  return (
    <div className={cn('flex flex-col h-full relative', className)}>
      {/* Message Area */}
      <ScrollArea
        ref={scrollAreaRef}
        className="flex-1"
        onScrollCapture={handleScroll}
      >
        <div className="p-4 space-y-4">
          {isEmpty ? (
            // Empty state
            <div className="flex flex-col items-center justify-center h-[60vh] text-center">
              <h2 className="text-xl font-semibold mb-2">
                TechTime Assistant
              </h2>
              <p className="text-muted-foreground mb-6 max-w-md">
                I can help diagnose and troubleshoot your network issues.
                Describe your problem or choose a common issue below.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-md">
                {SUGGESTIONS.map((suggestion) => (
                  <Button
                    key={suggestion}
                    variant="outline"
                    className="h-auto py-3 px-4 text-left justify-start"
                    onClick={() => handleSuggestionClick(suggestion)}
                  >
                    {suggestion}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            // Message list
            <>
              {messages.map((message, index) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  isLatest={index === messages.length - 1}
                />
              ))}

              {/* Tool execution */}
              {currentToolExecution && (
                <ToolExecutionCard
                  execution={{
                    toolName: currentToolExecution.name,
                    status: 'executing',
                    startTime: new Date()
                  }}
                />
              )}

              {/* Typing indicator */}
              {isStreaming && !currentToolExecution && (
                <div
                  className="flex items-center gap-1 p-2"
                  role="status"
                  aria-label="Assistant is typing"
                >
                  <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce" />
                  <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:0.1s]" />
                  <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:0.2s]" />
                </div>
              )}

              {/* Error */}
              {error && (
                <Card className="border-destructive bg-destructive/10">
                  <CardContent className="p-4 flex items-center justify-between">
                    <span className="text-destructive text-sm">
                      {error.message}
                    </span>
                    <Button variant="ghost" size="sm" onClick={retryLastMessage}>
                      <RefreshCw className="h-4 w-4 mr-1" />
                      Retry
                    </Button>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </div>
      </ScrollArea>

      {/* Scroll to bottom button */}
      {showScrollButton && (
        <Button
          variant="secondary"
          size="icon"
          className="absolute bottom-20 right-6 rounded-full shadow-lg"
          onClick={scrollToBottom}
          aria-label="Scroll to bottom"
        >
          <ArrowDown className="h-4 w-4" />
        </Button>
      )}

      {/* Input Area */}
      <div className="border-t p-4 bg-background">
        <div className="flex gap-2">
          <Textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your network issue..."
            disabled={isStreaming}
            className="min-h-[44px] max-h-32 resize-none"
            rows={1}
            aria-label="Message input"
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            size="icon"
            className="h-[44px] w-[44px]"
            aria-label="Send message"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
```

---

### Step 4.2.5: Create Chat Index Export

Create `components/chat/index.ts`:

```typescript
// components/chat/index.ts
export { MessageBubble } from './MessageBubble'
export { ToolExecutionCard } from './ToolExecutionCard'
export { ChatWindow } from './ChatWindow'
```

---

### Verification 4.2

```bash
npx tsc --noEmit
npm run lint
npm run build
```

**Checklist:**
- [ ] MessageBubble renders markdown for assistant messages
- [ ] MessageBubble has copy functionality
- [ ] ToolExecutionCard shows execution states
- [ ] ChatWindow has empty state with suggestions
- [ ] ChatWindow auto-scrolls on new messages
- [ ] All accessibility attributes present
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] Build passes

---

## Sub-Phase 4.3: Diagnostics Components

### Components to Build

| Component | File | Status |
|-----------|------|--------|
| ToolCard | `components/diagnostics/ToolCard.tsx` | New |
| OSILadderViz | `components/diagnostics/OSILadderViz.tsx` | New |
| ManualToolPanel | `components/diagnostics/ManualToolPanel.tsx` | New |

### Step 4.3.1: Create useOSILadder Hook

Create `hooks/use-osi-ladder.ts`:

```typescript
// hooks/use-osi-ladder.ts
'use client'

import { useState, useCallback, useMemo } from 'react'
import { DIAGNOSTIC_LAYERS } from '@/types'
import type { LayerState, LayerStatus, OSILayer } from '@/types'

export interface UseOSILadderOptions {
  initialLayers?: LayerState[]
  onLayerChange?: (layer: number, state: LayerStatus) => void
  onComplete?: (results: LayerState[]) => void
}

export interface UseOSILadderReturn {
  layers: LayerState[]
  currentLayer: number | null
  isComplete: boolean
  passedCount: number
  failedCount: number
  pendingCount: number
  overallStatus: 'pending' | 'passing' | 'failing' | 'complete'
  setLayerStatus: (layer: number, status: LayerStatus, result?: string) => void
  startLayer: (layer: number) => void
  passLayer: (layer: number, result?: string) => void
  failLayer: (layer: number, result?: string) => void
  reset: () => void
}

function createInitialLayers(): LayerState[] {
  return DIAGNOSTIC_LAYERS.map((layer) => ({
    layer,
    status: 'pending' as LayerStatus
  }))
}

export function useOSILadder(options: UseOSILadderOptions = {}): UseOSILadderReturn {
  const { initialLayers, onLayerChange, onComplete } = options

  const [layers, setLayers] = useState<LayerState[]>(
    initialLayers || createInitialLayers()
  )
  const [currentLayer, setCurrentLayer] = useState<number | null>(null)

  const setLayerStatus = useCallback(
    (layerNum: number, status: LayerStatus, result?: string) => {
      setLayers((prev) => {
        const updated = prev.map((l) =>
          l.layer.number === layerNum
            ? { ...l, status, testResult: result, testedAt: new Date() }
            : l
        )

        // Check if all complete
        const allComplete = updated.every(
          (l) =>
            l.status === 'pass' || l.status === 'fail' || l.status === 'skipped'
        )
        if (allComplete) {
          onComplete?.(updated)
        }

        return updated
      })
      onLayerChange?.(layerNum, status)
    },
    [onLayerChange, onComplete]
  )

  const startLayer = useCallback(
    (layerNum: number) => {
      setCurrentLayer(layerNum)
      setLayerStatus(layerNum, 'testing')
    },
    [setLayerStatus]
  )

  const passLayer = useCallback(
    (layerNum: number, result?: string) => {
      setLayerStatus(layerNum, 'pass', result)
      setCurrentLayer(null)
    },
    [setLayerStatus]
  )

  const failLayer = useCallback(
    (layerNum: number, result?: string) => {
      setLayerStatus(layerNum, 'fail', result)
      setCurrentLayer(null)
    },
    [setLayerStatus]
  )

  const reset = useCallback(() => {
    setLayers(createInitialLayers())
    setCurrentLayer(null)
  }, [])

  // Derived state
  const passedCount = useMemo(
    () => layers.filter((l) => l.status === 'pass').length,
    [layers]
  )
  const failedCount = useMemo(
    () => layers.filter((l) => l.status === 'fail').length,
    [layers]
  )
  const pendingCount = useMemo(
    () => layers.filter((l) => l.status === 'pending').length,
    [layers]
  )
  const isComplete = pendingCount === 0 && currentLayer === null

  const overallStatus = useMemo(() => {
    if (isComplete) return 'complete'
    if (failedCount > 0) return 'failing'
    if (passedCount > 0) return 'passing'
    return 'pending'
  }, [isComplete, failedCount, passedCount])

  return {
    layers,
    currentLayer,
    isComplete,
    passedCount,
    failedCount,
    pendingCount,
    overallStatus,
    setLayerStatus,
    startLayer,
    passLayer,
    failLayer,
    reset
  }
}
```

---

### Step 4.3.2: Create ToolCard Component

Create `components/diagnostics/ToolCard.tsx`:

```typescript
// components/diagnostics/ToolCard.tsx
'use client'

import { useState, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger
} from '@/components/ui/collapsible'
import { ChevronDown, Loader2, Play, Zap } from 'lucide-react'
import type { ToolCardProps, ToolParameter, ToolResult } from '@/types'

interface ParameterInputProps {
  param: ToolParameter
  value: unknown
  onChange: (value: unknown) => void
  disabled: boolean
}

function ParameterInput({ param, value, onChange, disabled }: ParameterInputProps) {
  switch (param.type) {
    case 'boolean':
      return (
        <Switch
          checked={Boolean(value)}
          onCheckedChange={onChange}
          disabled={disabled}
        />
      )
    case 'number':
      return (
        <Input
          type="number"
          value={(value as number) || ''}
          onChange={(e) => onChange(Number(e.target.value))}
          disabled={disabled}
          placeholder={String(param.default || '')}
        />
      )
    case 'string':
    default:
      return (
        <Input
          type="text"
          value={(value as string) || ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder={String(param.default || '')}
        />
      )
  }
}

interface ExtendedToolCardProps extends ToolCardProps {
  lastResult?: ToolResult
  className?: string
}

export function ToolCard({
  tool,
  isExpanded,
  isExecuting,
  onToggle,
  onExecute,
  lastResult,
  className
}: ExtendedToolCardProps) {
  const [params, setParams] = useState<Record<string, unknown>>(() => {
    // Initialize with defaults
    const defaults: Record<string, unknown> = {}
    tool.parameters.forEach((p) => {
      if (p.default !== undefined) {
        defaults[p.name] = p.default
      }
    })
    return defaults
  })

  const handleParamChange = useCallback((name: string, value: unknown) => {
    setParams((prev) => ({ ...prev, [name]: value }))
  }, [])

  const handleExecute = () => {
    // Validate required params
    const missingRequired = tool.parameters
      .filter((p) => p.required && params[p.name] === undefined)
      .map((p) => p.name)

    if (missingRequired.length > 0) {
      console.error('Missing required params:', missingRequired)
      return
    }

    onExecute(params)
  }

  const hasParameters = tool.parameters.length > 0

  return (
    <Card className={cn('overflow-hidden', className)}>
      <Collapsible open={isExpanded} onOpenChange={onToggle}>
        {/* Header */}
        <CollapsibleTrigger asChild>
          <div className="flex items-center justify-between p-3 cursor-pointer hover:bg-muted/50 transition-colors">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-muted-foreground" />
              <span className="font-mono text-sm font-medium">{tool.name}</span>
              <Badge variant="secondary" className="text-xs">
                {tool.category}
              </Badge>
            </div>
            <ChevronDown
              className={cn(
                'h-4 w-4 text-muted-foreground transition-transform',
                isExpanded && 'rotate-180'
              )}
            />
          </div>
        </CollapsibleTrigger>

        {/* Description (always visible) */}
        <div className="px-3 pb-3">
          <p className="text-sm text-muted-foreground">{tool.description}</p>
        </div>

        {/* Expanded content */}
        <CollapsibleContent>
          <div className="px-3 pb-3 space-y-4 border-t pt-3">
            {/* Parameters */}
            {hasParameters && (
              <div className="space-y-3">
                <h4 className="text-sm font-medium">Parameters</h4>
                <div className="grid gap-3">
                  {tool.parameters.map((param) => (
                    <div key={param.name} className="space-y-1">
                      <Label className="text-xs flex items-center gap-1">
                        {param.name}
                        {param.required && (
                          <span className="text-destructive">*</span>
                        )}
                      </Label>
                      <ParameterInput
                        param={param}
                        value={params[param.name]}
                        onChange={(v) => handleParamChange(param.name, v)}
                        disabled={isExecuting}
                      />
                      <p className="text-xs text-muted-foreground">
                        {param.description}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Execute button */}
            <Button
              onClick={handleExecute}
              disabled={isExecuting}
              className="w-full"
            >
              {isExecuting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Executing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Execute
                </>
              )}
            </Button>

            {/* Last result */}
            {lastResult && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Last Result</h4>
                <div className="bg-muted rounded-md p-3 font-mono text-xs max-h-48 overflow-auto">
                  {lastResult.error ? (
                    <span className="text-destructive">{lastResult.error}</span>
                  ) : (
                    <pre>
                      {typeof lastResult.result === 'object'
                        ? JSON.stringify(lastResult.result, null, 2)
                        : String(lastResult.result)}
                    </pre>
                  )}
                </div>
                {lastResult.duration && (
                  <p className="text-xs text-muted-foreground">
                    Completed in {lastResult.duration}ms
                  </p>
                )}
              </div>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
```

---

### Step 4.3.3: Create OSILadderViz Component

Create `components/diagnostics/OSILadderViz.tsx`:

```typescript
// components/diagnostics/OSILadderViz.tsx
'use client'

import { cn } from '@/lib/utils'
import { Progress } from '@/components/ui/progress'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Check, X, Minus, Circle, Loader2 } from 'lucide-react'
import type { OSILadderVizProps, LayerStatus } from '@/types'

const statusConfig: Record<
  LayerStatus,
  {
    icon: typeof Check
    className: string
    iconClass: string
  }
> = {
  pending: {
    icon: Circle,
    className: 'text-muted-foreground',
    iconClass: 'border-2 border-current rounded-full'
  },
  testing: {
    icon: Loader2,
    className: 'text-blue-500',
    iconClass: 'animate-spin'
  },
  pass: {
    icon: Check,
    className: 'text-green-500',
    iconClass: 'bg-green-500 text-white rounded-full p-0.5'
  },
  fail: {
    icon: X,
    className: 'text-red-500',
    iconClass: 'bg-red-500 text-white rounded-full p-0.5'
  },
  skipped: {
    icon: Minus,
    className: 'text-muted-foreground opacity-50',
    iconClass: ''
  }
}

interface ExtendedOSILadderVizProps extends OSILadderVizProps {
  showResults?: boolean
}

export function OSILadderViz({
  layers,
  currentLayer,
  onLayerClick,
  showResults = false,
  className
}: ExtendedOSILadderVizProps) {
  const passedCount = layers.filter((l) => l.status === 'pass').length
  const progress = (passedCount / layers.length) * 100
  const isInteractive = !!onLayerClick

  // Reverse layers for bottom-up display
  const displayLayers = [...layers].reverse()

  return (
    <div className={cn('space-y-4', className)}>
      {/* Ladder */}
      <div className="flex flex-col gap-1" role="list" aria-label="Network diagnostic layers">
        {displayLayers.map((layerState) => {
          const config = statusConfig[layerState.status]
          const Icon = config.icon
          const isActive = layerState.layer.number === currentLayer
          const layerNum = layerState.layer.number

          return (
            <Tooltip key={layerNum}>
              <TooltipTrigger asChild>
                <div
                  onClick={() => isInteractive && onLayerClick?.(layerNum)}
                  onKeyDown={(e) => {
                    if (isInteractive && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault()
                      onLayerClick?.(layerNum)
                    }
                  }}
                  className={cn(
                    'flex items-center gap-3 p-2 rounded-lg transition-colors',
                    isActive && 'bg-blue-500/10',
                    isInteractive && 'cursor-pointer hover:bg-muted',
                    config.className
                  )}
                  role={isInteractive ? 'button' : 'listitem'}
                  tabIndex={isInteractive ? 0 : undefined}
                  aria-current={isActive ? 'step' : undefined}
                  aria-label={`Layer ${layerNum}: ${layerState.layer.name} - ${layerState.status}`}
                >
                  {/* Layer number */}
                  <span className="w-6 text-center text-sm font-mono text-muted-foreground">
                    {layerNum}
                  </span>

                  {/* Status icon */}
                  <div className="w-6 h-6 flex items-center justify-center">
                    <Icon className={cn('h-4 w-4', config.iconClass)} />
                  </div>

                  {/* Layer name */}
                  <span
                    className={cn('flex-1 font-medium', isActive && 'text-blue-500')}
                  >
                    {layerState.layer.name}
                  </span>

                  {/* Status text */}
                  <span className="text-xs capitalize">{layerState.status}</span>
                </div>
              </TooltipTrigger>
              <TooltipContent side="right">
                <div className="space-y-1">
                  <p className="font-medium">{layerState.layer.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {layerState.layer.description}
                  </p>
                  {layerState.testResult && showResults && (
                    <p className="text-xs mt-2 font-mono">{layerState.testResult}</p>
                  )}
                </div>
              </TooltipContent>
            </Tooltip>
          )
        })}
      </div>

      {/* Progress bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Progress</span>
          <span>
            {passedCount}/{layers.length}
          </span>
        </div>
        <Progress value={progress} className="h-2" aria-label="Diagnostic progress" />
      </div>
    </div>
  )
}
```

---

### Step 4.3.4: Create ManualToolPanel Component

Create `components/diagnostics/ManualToolPanel.tsx`:

```typescript
// components/diagnostics/ManualToolPanel.tsx
'use client'

import { useState, useMemo } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger
} from '@/components/ui/accordion'
import { ToolCard } from './ToolCard'
import { Trash2 } from 'lucide-react'
import type { ManualToolPanelProps, DiagnosticTool, ToolResult } from '@/types'

const categoryLabels: Record<string, string> = {
  connectivity: 'Connectivity',
  dns: 'DNS',
  wifi: 'WiFi',
  ip_config: 'IP Configuration',
  system: 'System'
}

interface ExtendedManualToolPanelProps extends ManualToolPanelProps {
  results?: Map<string, ToolResult>
  executingTool?: string | null
  onClearAll?: () => void
}

export function ManualToolPanel({
  tools,
  onExecute,
  results = new Map(),
  executingTool = null,
  onClearAll,
  className
}: ExtendedManualToolPanelProps) {
  const [expandedTool, setExpandedTool] = useState<string | null>(null)

  // Group tools by category
  const toolsByCategory = useMemo(() => {
    const grouped = new Map<string, DiagnosticTool[]>()
    tools.forEach((tool) => {
      const category = tool.category
      if (!grouped.has(category)) {
        grouped.set(category, [])
      }
      grouped.get(category)!.push(tool)
    })
    return grouped
  }, [tools])

  const handleToggleTool = (toolName: string) => {
    setExpandedTool((prev) => (prev === toolName ? null : toolName))
  }

  const hasResults = results.size > 0

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <h3 className="font-semibold text-sm">Manual Diagnostics</h3>
        {hasResults && onClearAll && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={onClearAll}
          >
            <Trash2 className="h-3 w-3 mr-1" />
            Clear All
          </Button>
        )}
      </div>

      {/* Tool List */}
      <ScrollArea className="flex-1">
        <Accordion type="single" collapsible className="w-full">
          {Array.from(toolsByCategory.entries()).map(([category, categoryTools]) => (
            <AccordionItem key={category} value={category}>
              <AccordionTrigger className="px-3 py-2 hover:bg-muted/50">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">
                    {categoryLabels[category] || category}
                  </span>
                  <Badge variant="secondary" className="text-xs">
                    {categoryTools.length}
                  </Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-2 pb-2 space-y-2">
                {categoryTools.map((tool) => (
                  <ToolCard
                    key={tool.name}
                    tool={tool}
                    isExpanded={expandedTool === tool.name}
                    isExecuting={executingTool === tool.name}
                    onToggle={() => handleToggleTool(tool.name)}
                    onExecute={(params) => onExecute(tool.name, params)}
                    lastResult={results.get(tool.name)}
                  />
                ))}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </ScrollArea>
    </div>
  )
}
```

---

### Step 4.3.5: Create Diagnostics Index Export

Create `components/diagnostics/index.ts`:

```typescript
// components/diagnostics/index.ts
export { ToolCard } from './ToolCard'
export { OSILadderViz } from './OSILadderViz'
export { ManualToolPanel } from './ManualToolPanel'
```

---

### Step 4.3.6: Update Hooks Index

Update `hooks/index.ts`:

```typescript
// hooks/index.ts
export { useWebSocket } from './use-websocket'
export type { UseWebSocketOptions, UseWebSocketReturn } from './use-websocket'

export { useChat } from './use-chat'
export type { UseChatOptions, UseChatReturn } from './use-chat'

export { useOSILadder } from './use-osi-ladder'
export type { UseOSILadderOptions, UseOSILadderReturn } from './use-osi-ladder'
```

---

### Verification 4.3

```bash
npx tsc --noEmit
npm run lint
npm run build
```

**Checklist:**
- [ ] ToolCard renders parameters and handles execution
- [ ] OSILadderViz shows layer progress with icons
- [ ] ManualToolPanel groups tools by category
- [ ] useOSILadder hook manages layer state
- [ ] All accessibility attributes present
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] Build passes

---

## Sub-Phase 4.4: Analytics Components

### Components to Build

| Component | File | Status |
|-----------|------|--------|
| SummaryCards | `components/analytics/SummaryCards.tsx` | New |
| SessionsChart | `components/analytics/SessionsChart.tsx` | New |
| ToolStatsTable | `components/analytics/ToolStatsTable.tsx` | New |
| DateRangePicker | `components/analytics/DateRangePicker.tsx` | New |

### Step 4.4.1: Install Recharts

```bash
npm install recharts
```

---

### Step 4.4.2: Create SummaryCards Component

Create `components/analytics/SummaryCards.tsx`:

```typescript
// components/analytics/SummaryCards.tsx
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
        <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold tracking-tight">{value}</div>
        {(description || trend) && (
          <div className="flex items-center gap-1 mt-1">
            {trend && (
              <>
                {trend.isPositive ? (
                  <TrendingUp className="h-3 w-3 text-green-600" aria-hidden="true" />
                ) : (
                  <TrendingDown className="h-3 w-3 text-red-600" aria-hidden="true" />
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
              <span className="text-xs text-muted-foreground">{description}</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface ExtendedSummaryCardsProps extends SummaryCardsProps {
  className?: string
}

export function SummaryCards({
  summary,
  isLoading = false,
  className
}: ExtendedSummaryCardsProps) {
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
    <div
      className={cn(
        'grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
        className
      )}
    >
      {metrics.map((metric) => (
        <MetricCard key={metric.title} {...metric} isLoading={isLoading} />
      ))}
    </div>
  )
}
```

---

### Step 4.4.3: Create SessionsChart Component

Create `components/analytics/SessionsChart.tsx`:

```typescript
// components/analytics/SessionsChart.tsx
'use client'

import { useMemo } from 'react'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'
import { cn, formatDate, formatNumber } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type {
  SessionsChartProps,
  TimeSeriesPoint,
  CategoryBreakdown,
  ToolStats
} from '@/types'

const CHART_COLORS = [
  'hsl(var(--chart-1, 220 70% 50%))',
  'hsl(var(--chart-2, 160 60% 45%))',
  'hsl(var(--chart-3, 30 80% 55%))',
  'hsl(var(--chart-4, 280 65% 60%))',
  'hsl(var(--chart-5, 340 75% 55%))'
]

function ChartSkeleton() {
  return (
    <div className="w-full h-[300px] flex items-center justify-center">
      <Skeleton className="w-full h-full" />
    </div>
  )
}

interface ExtendedSessionsChartProps extends SessionsChartProps {
  title?: string
  isLoading?: boolean
}

export function SessionsChart({
  data,
  chartType,
  title = 'Sessions Over Time',
  isLoading = false,
  className
}: ExtendedSessionsChartProps) {
  const formattedData = useMemo(
    () =>
      data.map((point) => ({
        ...point,
        date: formatDate(point.timestamp, 'date'),
        value: point.value
      })),
    [data]
  )

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <ChartSkeleton />
        </CardContent>
      </Card>
    )
  }

  if (data.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="w-full h-[300px] flex items-center justify-center text-muted-foreground">
            No data available
          </div>
        </CardContent>
      </Card>
    )
  }

  const renderChart = () => {
    const commonProps = {
      data: formattedData,
      margin: { top: 5, right: 20, left: 10, bottom: 5 }
    }

    switch (chartType) {
      case 'area':
        return (
          <AreaChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
            <YAxis
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => formatNumber(value, 'compact')}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '6px'
              }}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="hsl(var(--primary))"
              fill="hsl(var(--primary))"
              fillOpacity={0.2}
              strokeWidth={2}
            />
          </AreaChart>
        )
      case 'bar':
        return (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
            <YAxis
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => formatNumber(value, 'compact')}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '6px'
              }}
            />
            <Bar dataKey="value" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
          </BarChart>
        )
      default:
        return (
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
            <YAxis
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => formatNumber(value, 'compact')}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '6px'
              }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        )
    }
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="w-full h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            {renderChart()}
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

// Category Pie Chart
interface CategoryChartProps {
  data: CategoryBreakdown[]
  title?: string
  isLoading?: boolean
  className?: string
}

export function CategoryChart({
  data,
  title = 'Issue Categories',
  isLoading = false,
  className
}: CategoryChartProps) {
  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <ChartSkeleton />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="w-full h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="count"
                nameKey="category"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={({ category, percentage }) =>
                  `${category} (${percentage.toFixed(1)}%)`
                }
              >
                {data.map((entry, index) => (
                  <Cell
                    key={entry.category}
                    fill={CHART_COLORS[index % CHART_COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

// Tool Usage Bar Chart
interface ToolUsageChartProps {
  data: ToolStats[]
  title?: string
  isLoading?: boolean
  className?: string
}

export function ToolUsageChart({
  data,
  title = 'Tool Usage',
  isLoading = false,
  className
}: ToolUsageChartProps) {
  const chartData = useMemo(
    () =>
      data
        .sort((a, b) => b.executionCount - a.executionCount)
        .slice(0, 10)
        .map((tool) => ({
          name: tool.toolName,
          count: tool.executionCount,
          successRate: tool.successRate
        })),
    [data]
  )

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <ChartSkeleton />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="w-full h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis type="number" tick={{ fontSize: 12 }} />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 12 }}
                width={120}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px'
                }}
              />
              <Bar dataKey="count" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
```

---

### Step 4.4.4: Create ToolStatsTable Component

Create `components/analytics/ToolStatsTable.tsx`:

```typescript
// components/analytics/ToolStatsTable.tsx
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
import type { ToolStatsTableProps, ToolStats } from '@/types'

type SortableColumn = keyof ToolStats

function getSuccessRateStyle(rate: number): string {
  if (rate >= 0.9)
    return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
  if (rate >= 0.7)
    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
  return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
}

function TableSkeleton() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <TableRow key={i}>
          <TableCell>
            <Skeleton className="h-4 w-32" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-16" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-16" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-16" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-16" />
          </TableCell>
        </TableRow>
      ))}
    </>
  )
}

interface ExtendedToolStatsTableProps extends ToolStatsTableProps {
  isLoading?: boolean
  className?: string
}

export function ToolStatsTable({
  stats,
  sortBy: externalSortBy,
  sortOrder: externalSortOrder,
  onSort,
  isLoading = false,
  className
}: ExtendedToolStatsTableProps) {
  // Internal sort state if not controlled
  const [internalSortBy, setInternalSortBy] =
    useState<SortableColumn>('executionCount')
  const [internalSortOrder, setInternalSortOrder] = useState<'asc' | 'desc'>('desc')

  const sortBy = externalSortBy ?? internalSortBy
  const sortOrder = externalSortOrder ?? internalSortOrder

  const handleSort = (column: SortableColumn) => {
    if (onSort) {
      onSort(column)
    } else {
      if (column === internalSortBy) {
        setInternalSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
      } else {
        setInternalSortBy(column)
        setInternalSortOrder('desc')
      }
    }
  }

  const sortedStats = useMemo(() => {
    if (!stats.length) return []

    return [...stats].sort((a, b) => {
      let aVal: number | string | Date = a[sortBy]
      let bVal: number | string | Date = b[sortBy]

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
    return sortOrder === 'asc' ? (
      <ArrowUp className="ml-1 h-4 w-4" />
    ) : (
      <ArrowDown className="ml-1 h-4 w-4" />
    )
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
              {columns.map((col) => (
                <TableHead
                  key={col.key}
                  className="cursor-pointer select-none hover:bg-muted"
                  onClick={() => handleSort(col.key)}
                  aria-sort={
                    col.key === sortBy
                      ? sortOrder === 'asc'
                        ? 'ascending'
                        : 'descending'
                      : 'none'
                  }
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
              sortedStats.map((stat) => (
                <TableRow key={stat.toolName}>
                  <TableCell className="font-mono text-sm">
                    {stat.toolName}
                  </TableCell>
                  <TableCell>{formatNumber(stat.executionCount)}</TableCell>
                  <TableCell>
                    <Badge
                      variant="secondary"
                      className={cn(
                        'font-mono',
                        getSuccessRateStyle(stat.successRate)
                      )}
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

### Step 4.4.5: Create DateRangePicker Component

Create `components/analytics/DateRangePicker.tsx`:

```typescript
// components/analytics/DateRangePicker.tsx
'use client'

import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { CalendarIcon } from 'lucide-react'

const presets = [
  { label: 'Last 7 days', value: '7' },
  { label: 'Last 30 days', value: '30' },
  { label: 'Last 90 days', value: '90' }
]

export function DateRangePicker() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [preset, setPreset] = useState(searchParams.get('days') || '7')

  const handlePresetChange = (value: string) => {
    setPreset(value)
    const params = new URLSearchParams(searchParams)
    params.set('days', value)
    router.push(`/dashboard?${params}`)
  }

  return (
    <Select value={preset} onValueChange={handlePresetChange}>
      <SelectTrigger className="w-40" aria-label="Select date range">
        <CalendarIcon className="mr-2 h-4 w-4" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {presets.map((p) => (
          <SelectItem key={p.value} value={p.value}>
            {p.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
```

---

### Step 4.4.6: Create Analytics Index Export

Create `components/analytics/index.ts`:

```typescript
// components/analytics/index.ts
export { SummaryCards
