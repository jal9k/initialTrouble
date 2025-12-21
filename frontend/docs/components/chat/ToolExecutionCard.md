# ToolExecutionCard Component

This document specifies the ToolExecutionCard component for displaying tool execution status.

## File Location

```
frontend/
  components/
    chat/
      ToolExecutionCard.tsx
```

---

## Overview

The ToolExecutionCard component displays:
- Current tool being executed
- Execution status (executing/success/error)
- Progress animation
- Result preview
- Expandable details

This component uses a **headless pattern** for maximum reusability.

---

## Headless API

### Hook Interface

```typescript
interface UseToolExecutionOptions {
  /** Initial tool state */
  initialState?: ToolExecutionState
  
  /** Callback on status change */
  onStatusChange?: (status: ToolExecutionStatus) => void
  
  /** Auto-collapse delay after success (ms) */
  autoCollapseDelay?: number
}

interface UseToolExecutionReturn {
  // State
  state: ToolExecutionState
  isExecuting: boolean
  isSuccess: boolean
  isError: boolean
  duration: number | null
  
  // Actions
  start: (toolName: string) => void
  complete: (result: unknown) => void
  fail: (error: string) => void
  reset: () => void
}
```

### Hook Implementation

```typescript
'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import type { ToolExecutionState, ToolExecutionStatus } from '@/types'

export function useToolExecution(
  options: UseToolExecutionOptions = {}
): UseToolExecutionReturn {
  const { initialState, onStatusChange, autoCollapseDelay } = options

  const [state, setState] = useState<ToolExecutionState>(
    initialState || {
      toolName: '',
      status: 'idle'
    }
  )

  const startTimeRef = useRef<Date | null>(null)

  // Notify on status change
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
    setState(prev => ({
      ...prev,
      status: 'success',
      endTime,
      result
    }))
  }, [])

  const fail = useCallback((error: string) => {
    const endTime = new Date()
    setState(prev => ({
      ...prev,
      status: 'error',
      endTime,
      error
    }))
  }, [])

  const reset = useCallback(() => {
    startTimeRef.current = null
    setState({
      toolName: '',
      status: 'idle'
    })
  }, [])

  const duration = state.startTime && state.endTime
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

## Props Interface

```typescript
interface ToolExecutionCardProps {
  /** Tool execution state */
  execution: ToolExecutionState
  
  /** Callback to cancel execution */
  onCancel?: () => void
  
  /** Whether to show detailed results */
  showDetails?: boolean
  
  /** Additional CSS classes */
  className?: string
}
```

---

## Component Structure

```
┌─────────────────────────────────────────────────────────────┐
│  ToolExecutionCard                                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ⚡ ping_gateway                        [Executing...] │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  ███████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  ToolExecutionCard (Success)                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ✓ ping_gateway                           [235ms]     │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  Gateway: 192.168.1.1                           │  │  │
│  │  │  Status: Reachable                              │  │  │
│  │  │  Latency: 12ms                          [▼]    │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component States

| State | Description | Visual |
|-------|-------------|--------|
| Idle | No execution | Not rendered |
| Executing | Tool running | Spinner, progress bar |
| Success | Completed successfully | Checkmark, green accent |
| Error | Execution failed | X icon, red accent |

---

## Behaviors

### Execution Animation
- Pulsing/bouncing spinner during execution
- Indeterminate progress bar
- Tool name displayed prominently

### Success State
- Checkmark icon replaces spinner
- Duration displayed
- Result preview shown
- Expandable for full details

### Error State
- X icon displayed
- Error message shown
- Retry button (if supported)

### Expand/Collapse
- Click to expand full result
- Syntax-highlighted JSON for objects
- Copy button for results

---

## shadcn/ui Dependencies

| Component | Usage |
|-----------|-------|
| `Card` | Container |
| `Badge` | Status indicator |
| `Button` | Cancel, expand actions |
| `Collapsible` | Expandable details |
| `Progress` | Execution progress |

---

## Styling Guidelines

### Status Colors
```css
.status-executing {
  @apply border-blue-500/50 bg-blue-50 dark:bg-blue-950/20;
}

.status-success {
  @apply border-green-500/50 bg-green-50 dark:bg-green-950/20;
}

.status-error {
  @apply border-red-500/50 bg-red-50 dark:bg-red-950/20;
}
```

### Animation
```css
.spinner {
  @apply animate-spin h-4 w-4;
}

.progress-indeterminate {
  @apply animate-pulse bg-gradient-to-r from-transparent via-primary to-transparent;
}

.status-enter {
  @apply animate-in fade-in slide-in-from-left-2 duration-200;
}
```

### Result Display
```css
.result-preview {
  @apply font-mono text-xs bg-muted rounded p-2 overflow-x-auto;
  @apply max-h-32 overflow-y-auto;
}
```

---

## Implementation

```typescript
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

export function ToolExecutionCard({
  execution,
  onCancel,
  showDetails = false,
  className
}: ToolExecutionCardProps) {
  const [isOpen, setIsOpen] = useState(showDetails)

  const config = statusConfig[execution.status]
  const Icon = config.icon
  const duration = execution.startTime && execution.endTime
    ? execution.endTime.getTime() - execution.startTime.getTime()
    : null

  if (execution.status === 'idle') {
    return null
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
            <div
              className="h-full bg-primary animate-pulse"
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
                      onClick={() => {
                        navigator.clipboard.writeText(
                          typeof execution.result === 'object'
                            ? JSON.stringify(execution.result, null, 2)
                            : String(execution.result)
                        )
                      }}
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

## Usage Example (Headless)

```typescript
'use client'

import { useToolExecution } from '@/hooks/use-tool-execution'

function CustomToolDisplay() {
  const {
    state,
    isExecuting,
    isSuccess,
    duration,
    start,
    complete,
    fail
  } = useToolExecution({
    onStatusChange: (status) => console.log('Status:', status)
  })

  // Trigger from external event
  useEffect(() => {
    start('ping_gateway')
    // Simulate completion
    setTimeout(() => {
      complete({ gateway: '192.168.1.1', reachable: true })
    }, 2000)
  }, [])

  return (
    <div>
      {isExecuting && <Spinner />}
      {isSuccess && (
        <div>
          Completed in {duration}ms
          <pre>{JSON.stringify(state.result)}</pre>
        </div>
      )}
    </div>
  )
}
```

---

## Accessibility

| Feature | Implementation |
|---------|---------------|
| Status announced | Live region for status changes |
| Keyboard expand | Space/Enter toggles details |
| Progress | ARIA progressbar role |
| Focus management | Focus moves appropriately |

---

## Test Specifications

### State Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Idle state not rendered | Component returns null |
| Executing shows spinner | Spinner icon animated |
| Success shows checkmark | Check icon displayed |
| Error shows X | X icon displayed |

### Content Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Tool name displayed | Name shown in header |
| Duration displayed | Time shown on completion |
| Result expandable | Click reveals full result |
| Error message shown | Error text visible |

### Interaction Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Cancel button calls onCancel | Callback invoked |
| Expand toggle works | Content shows/hides |
| Copy button copies result | Content in clipboard |

### Animation Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Entry animation plays | Fade/slide on mount |
| Spinner rotates | Continuous rotation |
| Progress bar animates | Shimmer effect |

### Hook Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| `start` sets executing | Status becomes 'executing' |
| `complete` sets success | Status becomes 'success' |
| `fail` sets error | Status becomes 'error' |
| Duration calculated | Correct time difference |

---

## Lint/Build Verification

- [ ] Component properly typed
- [ ] Hook follows headless pattern
- [ ] All states handled
- [ ] Animations performant
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All tests pass

---

## Related Documents

- [ChatWindow.md](./ChatWindow.md) - Parent component
- [MessageBubble.md](./MessageBubble.md) - Message display
- [use-chat.md](../../hooks/use-chat.md) - Provides tool execution state
- [headless-patterns.md](../../headless-patterns.md) - Headless pattern guide

