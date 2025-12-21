# Headless Component Architecture

This guide establishes the headless component patterns used throughout the Network Diagnostics frontend. Headless components separate logic from presentation, enabling maximum reusability.

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Headless Pattern                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────────────┐                                   │
│   │   Custom Hook       │  ← Pure logic, no UI              │
│   │   (useChat, etc.)   │                                   │
│   └──────────┬──────────┘                                   │
│              │                                               │
│              │ returns { state, actions }                   │
│              ▼                                               │
│   ┌─────────────────────┐                                   │
│   │   Styled Component  │  ← Consumes hook, renders UI      │
│   │   (ChatWindow)      │                                   │
│   └─────────────────────┘                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Core Principles

### 1. Separation of Concerns

| Layer | Responsibility | Example |
|-------|---------------|---------|
| **Hook** | State, side effects, event handlers | `useChat()` |
| **Component** | Layout, styling, accessibility | `<ChatWindow />` |
| **Styles** | Visual appearance | Tailwind classes |

### 2. Inversion of Control

The hook controls **what** happens, the component controls **how** it looks:

```typescript
// Hook controls logic
const { messages, sendMessage, isConnected } = useChat()

// Component controls presentation
return (
  <div className="flex flex-col h-full">
    {messages.map(msg => <MessageBubble key={msg.id} {...msg} />)}
  </div>
)
```

### 3. Composability

Headless hooks can be composed together:

```typescript
function useChatWithTools() {
  const chat = useChat()
  const tools = useToolExecution()
  
  return {
    ...chat,
    ...tools,
    executeToolFromChat: (toolName: string) => {
      tools.execute(toolName)
      chat.addSystemMessage(`Executing ${toolName}...`)
    }
  }
}
```

---

## Hook Pattern Template

### Basic Structure

```typescript
interface UseExampleOptions {
  initialValue?: string
  onSuccess?: (result: Result) => void
  onError?: (error: Error) => void
}

interface UseExampleReturn {
  // State
  value: string
  isLoading: boolean
  error: Error | null
  
  // Actions
  setValue: (value: string) => void
  submit: () => Promise<void>
  reset: () => void
}

export function useExample(options: UseExampleOptions = {}): UseExampleReturn {
  const { initialValue = '', onSuccess, onError } = options
  
  // State
  const [value, setValue] = useState(initialValue)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  
  // Actions
  const submit = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await api.submit(value)
      onSuccess?.(result)
    } catch (e) {
      const err = e instanceof Error ? e : new Error('Unknown error')
      setError(err)
      onError?.(err)
    } finally {
      setIsLoading(false)
    }
  }, [value, onSuccess, onError])
  
  const reset = useCallback(() => {
    setValue(initialValue)
    setError(null)
  }, [initialValue])
  
  return {
    value,
    isLoading,
    error,
    setValue,
    submit,
    reset
  }
}
```

### Return Value Categories

Every headless hook should return values organized into these categories:

| Category | Description | Examples |
|----------|-------------|----------|
| **State** | Current values, readonly | `messages`, `isLoading`, `error` |
| **Derived State** | Computed from state | `isEmpty`, `hasError`, `canSubmit` |
| **Actions** | Functions to modify state | `send()`, `reset()`, `retry()` |
| **Refs** | DOM references if needed | `containerRef`, `inputRef` |

---

## State-Heavy Components

The following components require headless APIs:

### 1. useWebSocket

**Purpose:** Manage WebSocket connection lifecycle

```typescript
interface UseWebSocketReturn {
  // State
  isConnected: boolean
  isConnecting: boolean
  error: Error | null
  lastMessage: WebSocketMessage | null
  
  // Actions
  connect: () => void
  disconnect: () => void
  send: (message: unknown) => void
}
```

### 2. useChat

**Purpose:** Manage chat state machine

```typescript
interface UseChatReturn {
  // State
  messages: Message[]
  isStreaming: boolean
  conversationId: string | null
  
  // Derived
  isEmpty: boolean
  lastMessage: Message | null
  
  // Actions
  sendMessage: (content: string) => Promise<void>
  clearMessages: () => void
  loadConversation: (id: string) => Promise<void>
}
```

### 3. useToolExecution

**Purpose:** Manage diagnostic tool execution

```typescript
interface UseToolExecutionReturn {
  // State
  currentTool: string | null
  isExecuting: boolean
  result: ToolResult | null
  error: Error | null
  
  // Actions
  execute: (toolName: string, params?: Record<string, unknown>) => Promise<void>
  cancel: () => void
  reset: () => void
}
```

### 4. useOSILadder

**Purpose:** Manage OSI layer diagnostic states

```typescript
interface UseOSILadderReturn {
  // State
  layers: LayerState[]
  currentLayer: number | null
  
  // Derived
  passedLayers: number
  failedLayers: number
  
  // Actions
  setLayerState: (layer: number, state: 'pending' | 'testing' | 'pass' | 'fail') => void
  reset: () => void
}
```

### 5. useManualToolPanel

**Purpose:** Manage manual tool panel state

```typescript
interface UseManualToolPanelReturn {
  // State
  tools: Tool[]
  expandedTool: string | null
  parameters: Record<string, Record<string, unknown>>
  
  // Actions
  toggleTool: (toolName: string) => void
  setParameter: (toolName: string, param: string, value: unknown) => void
  executeTool: (toolName: string) => Promise<void>
}
```

---

## Component Pattern Template

### Consuming a Headless Hook

```typescript
'use client'

import { useExample } from '@/hooks/use-example'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface ExampleComponentProps {
  className?: string
  onSubmitSuccess?: () => void
}

export function ExampleComponent({ 
  className,
  onSubmitSuccess 
}: ExampleComponentProps) {
  const {
    value,
    isLoading,
    error,
    setValue,
    submit,
    reset
  } = useExample({
    onSuccess: onSubmitSuccess
  })
  
  return (
    <div className={cn('space-y-4', className)}>
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={isLoading}
        aria-invalid={!!error}
      />
      
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error.message}
        </p>
      )}
      
      <div className="flex gap-2">
        <Button onClick={submit} disabled={isLoading}>
          {isLoading ? 'Submitting...' : 'Submit'}
        </Button>
        <Button variant="outline" onClick={reset}>
          Reset
        </Button>
      </div>
    </div>
  )
}
```

### Render Props Pattern (Alternative)

For maximum flexibility, expose render props:

```typescript
interface ExampleRenderProps {
  value: string
  isLoading: boolean
  error: Error | null
  setValue: (value: string) => void
  submit: () => Promise<void>
}

interface ExampleHeadlessProps {
  children: (props: ExampleRenderProps) => React.ReactNode
}

export function ExampleHeadless({ children }: ExampleHeadlessProps) {
  const props = useExample()
  return <>{children(props)}</>
}

// Usage
<ExampleHeadless>
  {({ value, submit }) => (
    <CustomUI value={value} onSubmit={submit} />
  )}
</ExampleHeadless>
```

---

## Testing Headless Components

### Testing Hooks

```typescript
import { renderHook, act } from '@testing-library/react'
import { useExample } from '@/hooks/use-example'

describe('useExample', () => {
  it('should initialize with default value', () => {
    const { result } = renderHook(() => useExample())
    expect(result.current.value).toBe('')
  })
  
  it('should update value', () => {
    const { result } = renderHook(() => useExample())
    act(() => {
      result.current.setValue('test')
    })
    expect(result.current.value).toBe('test')
  })
  
  it('should handle submit', async () => {
    const onSuccess = jest.fn()
    const { result } = renderHook(() => useExample({ onSuccess }))
    
    await act(async () => {
      await result.current.submit()
    })
    
    expect(onSuccess).toHaveBeenCalled()
  })
})
```

### Testing Styled Components

```typescript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ExampleComponent } from '@/components/ExampleComponent'

// Mock the hook
jest.mock('@/hooks/use-example', () => ({
  useExample: () => ({
    value: 'test',
    isLoading: false,
    error: null,
    setValue: jest.fn(),
    submit: jest.fn(),
    reset: jest.fn()
  })
}))

describe('ExampleComponent', () => {
  it('should render input with value', () => {
    render(<ExampleComponent />)
    expect(screen.getByRole('textbox')).toHaveValue('test')
  })
})
```

---

## Best Practices

### Do

- Keep hooks focused on a single concern
- Return stable references using `useCallback` and `useMemo`
- Provide sensible defaults for all options
- Include cleanup in `useEffect` hooks
- Type all return values explicitly

### Don't

- Don't include JSX in hooks
- Don't access DOM directly in hooks (use refs)
- Don't have side effects outside of `useEffect`
- Don't mutate state directly
- Don't create new object/array references on every render

---

## Migration Guide

When converting an existing component to headless:

1. **Extract state** - Move all `useState` calls to the hook
2. **Extract effects** - Move all `useEffect` calls to the hook
3. **Extract handlers** - Move event handlers to the hook
4. **Define interface** - Create explicit return type interface
5. **Update component** - Consume the hook in the component
6. **Test separately** - Write tests for hook and component independently

---

## Related Documents

- [use-chat.md](./hooks/use-chat.md) - Chat state hook specification
- [use-websocket.md](./hooks/use-websocket.md) - WebSocket hook specification
- [ChatWindow.md](./components/chat/ChatWindow.md) - Chat component specification
- [OSILadderViz.md](./components/diagnostics/OSILadderViz.md) - OSI ladder specification

