# Phase 4.2: Chat Components

Implementing MessageBubble, ToolExecutionCard, and ChatWindow.

---

## Prerequisites

- Phase 4.1 completed
- `useChat` hook from Phase 3

---

## Step 1: Install Dependencies

```bash
npm install react-markdown remark-gfm
```

---

## Step 2: Create useToolExecution Hook

Create `hooks/use-tool-execution.ts`:

```typescript
// hooks/use-tool-execution.ts
'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import type { ToolExecutionState, ToolExecutionStatus } from '@/types'

interface UseToolExecutionOptions {
  initialState?: ToolExecutionState
  onStatusChange?: (status: ToolExecutionStatus) => void
  autoCollapseDelay?: number
}

interface UseToolExecutionReturn {
  state: ToolExecutionState
  isExecuting: boolean
  isSuccess: boolean
  isError: boolean
  duration: number | null
  start: (toolName: string) => void
  complete: (result: unknown) => void
  fail: (error: string) => void
  reset: () => void
}

export function useToolExecution(
  options: UseToolExecutionOptions = {}
): UseToolExecutionReturn {
  const { initialState, onStatusChange } = options

  const [state, setState] = useState<ToolExecutionState>(
    initialState || { toolName: '', status: 'idle' }
  )

  const startTimeRef = useRef<Date | null>(null)

  useEffect(() => {
    onStatusChange?.(state.status)
  }, [state.status, onStatusChange])

  const start = useCallback((toolName: string) => {
    startTimeRef.current = new Date()
    setState({
      toolName,
      status: 'executing',
      startTime: startTimeRef.current
    })
  }, [])

  const complete = useCallback((result: unknown) => {
    const endTime = new Date()
    setState((prev) => ({
      ...prev,
      status: 'success',
      endTime,
      result
    }))
  }, [])

  const fail = useCallback((error: string) => {
    const endTime = new Date()
    setState((prev) => ({
      ...prev,
      status: 'error',
      endTime,
      error
    }))
  }, [])

  const reset = useCallback(() => {
    startTimeRef.current = null
    setState({ toolName: '', status: 'idle' })
  }, [])

  const duration =
    state.startTime && state.endTime
      ? state.endTime.getTime() - state.startTime.getTime()
      : null

  return {
    state,
    isExecuting: state.status === 'executing',
    isSuccess: state.status === 'success',
    isError: state.status === 'error',
    duration,
    start,
    complete,
    fail,
    reset
  }
}
```

---

## Step 3: Create MessageBubble Component

Create `components/chat/MessageBubble.tsx`:

```typescript
// components/chat/MessageBubble.tsx
'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn, formatDate } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from '@/components/ui/tooltip'
import { Check, Copy, Zap } from 'lucide-react'
import type { Message } from '@/types'

const roleStyles: Record<string, string> = {
  user: 'ml-auto bg-primary text-primary-foreground rounded-2xl rounded-br-md',
  assistant: 'mr-auto bg-muted rounded-2xl rounded-bl-md',
  system: 'mx-auto text-muted-foreground text-sm text-center italic',
  tool: 'mr-auto bg-muted/50 border rounded-lg font-mono text-sm'
}

interface MessageBubbleProps {
  message: Message
  isLatest?: boolean
  showTimestamp?: boolean
  className?: string
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
              code: ({ className, children, ...props }) => {
                const isInline = !className
                if (isInline) {
                  return (
                    <code className="bg-muted px-1 py-0.5 rounded text-sm">
                      {children}
                    </code>
                  )
                }
                return (
                  <pre className="bg-muted rounded-md p-3 overflow-x-auto">
                    <code className={className} {...props}>
                      {children}
                    </code>
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

## Step 4: Create ToolExecutionCard Component

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
import type { ToolExecutionState } from '@/types'

const statusConfig = {
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

interface ToolExecutionCardProps {
  execution: ToolExecutionState
  onCancel?: () => void
  showDetails?: boolean
  className?: string
}

export function ToolExecutionCard({
  execution,
  onCancel,
  showDetails = false,
  className
}: ToolExecutionCardProps) {
  const [isOpen, setIsOpen] = useState(showDetails)

  const config = statusConfig[execution.status]
  const Icon = config.icon
  const duration =
    execution.startTime && execution.endTime
      ? execution.endTime.getTime() - execution.startTime.getTime()
      : null

  if (execution.status === 'idle') {
    return null
  }

  const handleCopy = () => {
    const content =
      typeof execution.result === 'object'
        ? JSON.stringify(execution.result, null, 2)
        : String(execution.result)
    navigator.clipboard.writeText(content)
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
            <div className="h-full w-full bg-primary/50 animate-pulse" />
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
                    >
                      <Copy className="h-3 w-3" />
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

## Step 5: Create ChatWindow Component

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

const SUGGESTIONS = [
  "My WiFi keeps disconnecting",
  "I can't access the internet",
  "DNS resolution is failing",
  "Slow network speeds"
]

interface ChatWindowProps extends UseChatOptions {
  className?: string
}

export function ChatWindow({ className, ...chatOptions }: ChatWindowProps) {
  const {
    messages,
    isStreaming,
    isEmpty,
    error,
    currentToolExecution,
    sendMessage,
    retryLastMessage
  } = useChat(chatOptions)

  const [input, setInput] = useState('')
  const [showScrollButton, setShowScrollButton] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollAreaRef.current) {
      const viewport = scrollAreaRef.current.querySelector(
        '[data-radix-scroll-area-viewport]'
      )
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight
      }
    }
  }, [messages, currentToolExecution])

  // Handle scroll position for "scroll to bottom" button
  const handleScroll = useCallback(() => {
    if (scrollAreaRef.current) {
      const viewport = scrollAreaRef.current.querySelector(
        '[data-radix-scroll-area-viewport]'
      ) as HTMLElement
      if (viewport) {
        const isNearBottom =
          viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight < 100
        setShowScrollButton(!isNearBottom)
      }
    }
  }, [])

  // Scroll to bottom handler
  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const viewport = scrollAreaRef.current.querySelector(
        '[data-radix-scroll-area-viewport]'
      )
      if (viewport) {
        viewport.scrollTo({
          top: viewport.scrollHeight,
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
                Network Diagnostics Assistant
              </h2>
              <p className="text-muted-foreground mb-6 max-w-md">
                I can help diagnose and troubleshoot your network issues.
                Describe your problem or choose a common issue below.
              </p>
              <div className="grid grid-cols-2 gap-2 max-w-md">
                {SUGGESTIONS.map((suggestion) => (
                  <Button
                    key={suggestion}
                    variant="outline"
                    className="h-auto py-3 px-4 text-left"
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
                <div className="flex items-center gap-1 p-2">
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
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            size="icon"
            className="h-[44px] w-[44px]"
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

## Step 6: Create Chat Index Export

Create `components/chat/index.ts`:

```typescript
// components/chat/index.ts

export { ChatWindow } from './ChatWindow'
export { MessageBubble } from './MessageBubble'
export { ToolExecutionCard } from './ToolExecutionCard'
```

---

## Step 7: Update Hooks Index

Update `hooks/index.ts`:

```typescript
// hooks/index.ts

export { useWebSocket } from './use-websocket'
export type { UseWebSocketOptions, UseWebSocketReturn } from './use-websocket'

export { useChat } from './use-chat'
export type { UseChatOptions, UseChatReturn } from './use-chat'

export { useToolExecution } from './use-tool-execution'
```

---

## Step 8: Verify Phase 4.2

```bash
npx tsc --noEmit && npm run lint && npm run build
```

---

## Phase 4.2 Checklist

- [ ] react-markdown and remark-gfm installed
- [ ] useToolExecution hook created
- [ ] MessageBubble with markdown rendering
- [ ] MessageBubble copy button works
- [ ] MessageBubble shows timestamps
- [ ] ToolExecutionCard with all states
- [ ] ToolExecutionCard expand/collapse
- [ ] ChatWindow with auto-scroll
- [ ] ChatWindow empty state with suggestions
- [ ] ChatWindow typing indicator
- [ ] ChatWindow error with retry
- [ ] `tsc --noEmit` passes
- [ ] `npm run lint` passes
- [ ] `npm run build` passes

**Gate: All checks must pass before proceeding to Phase 4.3**


