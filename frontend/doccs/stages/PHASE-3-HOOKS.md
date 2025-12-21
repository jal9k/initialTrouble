# Phase 3: Hooks

React hooks for WebSocket connection and chat state management.

---

## Step 1: Create useWebSocket Hook

Create `hooks/use-websocket.ts`:

```typescript
// hooks/use-websocket.ts

'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { ChatWebSocket, WebSocketConfig } from '@/lib/websocket'
import type { ConnectionState, ServerMessage, ClientMessage, WebSocketError } from '@/types'

// ============================================================================
// Hook Options
// ============================================================================

export interface UseWebSocketOptions {
  url?: string
  autoConnect?: boolean
  reconnect?: boolean
  reconnectInterval?: number
  maxReconnectAttempts?: number
  onMessage?: (message: ServerMessage) => void
  onOpen?: () => void
  onClose?: (event: CloseEvent) => void
  onError?: (error: Event) => void
}

// ============================================================================
// Hook Return Type
// ============================================================================

export interface UseWebSocketReturn {
  // State
  isConnected: boolean
  isConnecting: boolean
  connectionState: ConnectionState
  error: WebSocketError | null
  lastMessage: ServerMessage | null

  // Derived State
  canSend: boolean
  reconnectAttempts: number

  // Actions
  connect: () => void
  disconnect: () => void
  send: (message: ClientMessage) => void
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    url,
    autoConnect = true,
    reconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
    onMessage,
    onOpen,
    onClose,
    onError
  } = options

  // State
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected')
  const [error, setError] = useState<WebSocketError | null>(null)
  const [lastMessage, setLastMessage] = useState<ServerMessage | null>(null)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)

  // Refs
  const wsRef = useRef<ChatWebSocket | null>(null)
  const callbacksRef = useRef({ onMessage, onOpen, onClose, onError })

  // Keep callbacks ref updated
  useEffect(() => {
    callbacksRef.current = { onMessage, onOpen, onClose, onError }
  }, [onMessage, onOpen, onClose, onError])

  // Initialize WebSocket client
  useEffect(() => {
    wsRef.current = new ChatWebSocket({
      url,
      reconnect,
      reconnectInterval,
      maxReconnectAttempts,
      onOpen: () => {
        setConnectionState('connected')
        setError(null)
        setReconnectAttempts(0)
        callbacksRef.current.onOpen?.()
      },
      onClose: (event) => {
        setConnectionState('disconnected')
        callbacksRef.current.onClose?.(event)
      },
      onError: (event) => {
        setConnectionState('error')
        const wsError: WebSocketError = {
          code: 0,
          reason: 'Connection error',
          timestamp: new Date()
        }
        setError(wsError)
        callbacksRef.current.onError?.(event)
      },
      onMessage: (message) => {
        setLastMessage(message)
        callbacksRef.current.onMessage?.(message)
      }
    })

    if (autoConnect) {
      setConnectionState('connecting')
      wsRef.current.connect()
    }

    return () => {
      wsRef.current?.disconnect()
    }
  }, [url, reconnect, reconnectInterval, maxReconnectAttempts, autoConnect])

  // Actions
  const connect = useCallback(() => {
    setConnectionState('connecting')
    wsRef.current?.connect()
  }, [])

  const disconnect = useCallback(() => {
    wsRef.current?.disconnect()
    setConnectionState('disconnected')
  }, [])

  const send = useCallback((message: ClientMessage) => {
    wsRef.current?.send(message)
  }, [])

  // Derived state
  const isConnected = connectionState === 'connected'
  const isConnecting = connectionState === 'connecting'
  const canSend = isConnected

  return {
    // State
    isConnected,
    isConnecting,
    connectionState,
    error,
    lastMessage,

    // Derived
    canSend,
    reconnectAttempts,

    // Actions
    connect,
    disconnect,
    send
  }
}
```

---

## Step 2: Create useChat Hook

Create `hooks/use-chat.ts`:

```typescript
// hooks/use-chat.ts

'use client'

import { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import { useWebSocket } from './use-websocket'
import { getSessionMessages } from '@/lib/api'
import { generateId } from '@/lib/utils'
import type {
  Message,
  ToolCall,
  ToolResult,
  ServerMessage,
  SessionOutcome
} from '@/types'

// ============================================================================
// Hook Options
// ============================================================================

export interface UseChatOptions {
  initialConversationId?: string
  onSessionStart?: (conversationId: string) => void
  onSessionEnd?: (outcome: SessionOutcome) => void
  onMessage?: (message: Message) => void
  onToolStart?: (toolCall: ToolCall) => void
  onToolComplete?: (result: ToolResult) => void
  persist?: boolean
}

// ============================================================================
// Hook Return Type
// ============================================================================

export interface UseChatReturn {
  // State
  messages: Message[]
  conversationId: string | null
  isStreaming: boolean
  isLoading: boolean
  error: Error | null
  currentToolExecution: ToolCall | null

  // Derived State
  isEmpty: boolean
  lastMessage: Message | null
  lastUserMessage: Message | null
  lastAssistantMessage: Message | null
  messageCount: number
  toolsUsed: string[]

  // Actions
  sendMessage: (content: string) => Promise<void>
  clearMessages: () => void
  loadConversation: (conversationId: string) => Promise<void>
  startNewConversation: () => void
  endConversation: (outcome: SessionOutcome) => void
  retryLastMessage: () => Promise<void>
}

// ============================================================================
// Constants
// ============================================================================

const STORAGE_KEY = 'network_diag_chat'

// ============================================================================
// Hook Implementation
// ============================================================================

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const {
    initialConversationId,
    onSessionStart,
    onSessionEnd,
    onMessage,
    onToolStart,
    onToolComplete,
    persist = true
  } = options

  // State
  const [messages, setMessages] = useState<Message[]>([])
  const [conversationId, setConversationId] = useState<string | null>(
    initialConversationId || null
  )
  const [isStreaming, setIsStreaming] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [currentToolExecution, setCurrentToolExecution] = useState<ToolCall | null>(null)

  // Refs
  const pendingMessageRef = useRef<string | null>(null)
  const callbacksRef = useRef({
    onSessionStart,
    onSessionEnd,
    onMessage,
    onToolStart,
    onToolComplete
  })

  // Update callbacks ref
  useEffect(() => {
    callbacksRef.current = {
      onSessionStart,
      onSessionEnd,
      onMessage,
      onToolStart,
      onToolComplete
    }
  }, [onSessionStart, onSessionEnd, onMessage, onToolStart, onToolComplete])

  // Handle incoming WebSocket messages
  const handleWebSocketMessage = useCallback(
    (serverMessage: ServerMessage) => {
      // Handle tool calls
      if (serverMessage.tool_calls?.length) {
        const toolCall = serverMessage.tool_calls[0]
        setCurrentToolExecution(toolCall)
        callbacksRef.current.onToolStart?.(toolCall)
      }

      // Handle response text
      if (serverMessage.response) {
        setIsStreaming(false)
        setCurrentToolExecution(null)

        const assistantMessage: Message = {
          id: generateId('msg'),
          role: 'assistant',
          content: serverMessage.response,
          timestamp: new Date(),
          toolCalls: serverMessage.tool_calls || undefined
        }

        setMessages((prev) => [...prev, assistantMessage])
        callbacksRef.current.onMessage?.(assistantMessage)

        // Handle tool results
        if (serverMessage.tool_calls?.length) {
          serverMessage.tool_calls.forEach((tc) => {
            const result: ToolResult = {
              toolCallId: tc.id,
              name: tc.name,
              result: tc.arguments
            }
            callbacksRef.current.onToolComplete?.(result)
          })
        }
      }

      // Update conversation ID
      if (serverMessage.conversation_id && !conversationId) {
        setConversationId(serverMessage.conversation_id)
        callbacksRef.current.onSessionStart?.(serverMessage.conversation_id)
      }
    },
    [conversationId]
  )

  // WebSocket connection
  const { send, isConnected } = useWebSocket({
    onMessage: handleWebSocketMessage
  })

  // Load from localStorage on mount
  useEffect(() => {
    if (persist && !initialConversationId && typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (stored) {
          const parsed = JSON.parse(stored)
          if (parsed.messages) {
            // Convert date strings back to Date objects
            const messagesWithDates = parsed.messages.map((m: Message) => ({
              ...m,
              timestamp: new Date(m.timestamp)
            }))
            setMessages(messagesWithDates)
          }
          if (parsed.conversationId) {
            setConversationId(parsed.conversationId)
          }
        }
      } catch {
        // Ignore parse errors
      }
    }
  }, [persist, initialConversationId])

  // Save to localStorage on message changes
  useEffect(() => {
    if (persist && messages.length > 0 && typeof window !== 'undefined') {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          messages,
          conversationId
        })
      )
    }
  }, [persist, messages, conversationId])

  // Actions
  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return

      setError(null)
      setIsStreaming(true)

      // Add user message
      const userMessage: Message = {
        id: generateId('msg'),
        role: 'user',
        content: content.trim(),
        timestamp: new Date()
      }

      setMessages((prev) => [...prev, userMessage])
      pendingMessageRef.current = content.trim()

      // Send via WebSocket
      send({
        message: content.trim(),
        conversation_id: conversationId || undefined
      })
    },
    [conversationId, send]
  )

  const clearMessages = useCallback(() => {
    setMessages([])
    setConversationId(null)
    setError(null)
    setCurrentToolExecution(null)
    if (persist && typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [persist])

  const loadConversation = useCallback(async (id: string) => {
    setIsLoading(true)
    setError(null)

    try {
      const loadedMessages = await getSessionMessages(id)
      // Convert date strings to Date objects
      const messagesWithDates = loadedMessages.map((m) => ({
        ...m,
        timestamp: new Date(m.timestamp)
      }))
      setMessages(messagesWithDates)
      setConversationId(id)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load conversation'))
    } finally {
      setIsLoading(false)
    }
  }, [])

  const startNewConversation = useCallback(() => {
    clearMessages()
  }, [clearMessages])

  const endConversation = useCallback(
    (outcome: SessionOutcome) => {
      callbacksRef.current.onSessionEnd?.(outcome)
    },
    []
  )

  const retryLastMessage = useCallback(async () => {
    if (pendingMessageRef.current) {
      // Remove last assistant message if it exists
      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1]
        if (lastMsg?.role === 'assistant') {
          return prev.slice(0, -1)
        }
        return prev
      })
      await sendMessage(pendingMessageRef.current)
    }
  }, [sendMessage])

  // Derived state
  const isEmpty = messages.length === 0
  const lastMessage = messages[messages.length - 1] || null
  const lastUserMessage = useMemo(
    () => [...messages].reverse().find((m) => m.role === 'user') || null,
    [messages]
  )
  const lastAssistantMessage = useMemo(
    () => [...messages].reverse().find((m) => m.role === 'assistant') || null,
    [messages]
  )
  const messageCount = messages.length
  const toolsUsed = useMemo(() => {
    const tools = new Set<string>()
    messages.forEach((msg) => {
      msg.toolCalls?.forEach((tc) => tools.add(tc.name))
    })
    return Array.from(tools)
  }, [messages])

  return {
    // State
    messages,
    conversationId,
    isStreaming,
    isLoading,
    error,
    currentToolExecution,

    // Derived
    isEmpty,
    lastMessage,
    lastUserMessage,
    lastAssistantMessage,
    messageCount,
    toolsUsed,

    // Actions
    sendMessage,
    clearMessages,
    loadConversation,
    startNewConversation,
    endConversation,
    retryLastMessage
  }
}
```

---

## Step 3: Create Index Export

Create `hooks/index.ts`:

```typescript
// hooks/index.ts

export { useWebSocket } from './use-websocket'
export type { UseWebSocketOptions, UseWebSocketReturn } from './use-websocket'

export { useChat } from './use-chat'
export type { UseChatOptions, UseChatReturn } from './use-chat'
```

---

## Step 4: Update Header to Use Hook

Update `components/layout/Header.tsx`:

```typescript
// components/layout/Header.tsx

'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Moon, Sun, Wifi, WifiOff } from 'lucide-react'
import { useTheme } from 'next-themes'
import { useWebSocket } from '@/hooks/use-websocket'

const navItems = [
  { href: '/chat', label: 'Chat' },
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/history', label: 'History' }
]

export function Header({ className }: { className?: string }) {
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
        </div>
      </div>
    </header>
  )
}
```

---

## Step 5: Verify Phase 3

```bash
# Type check
npm run type-check || npx tsc --noEmit

# Lint
npm run lint

# Build
npm run build

# Start dev server to verify hooks work
npm run dev
```

---

## Phase 3 Checklist

- [ ] `hooks/use-websocket.ts` created
- [ ] `hooks/use-chat.ts` created
- [ ] `hooks/index.ts` created with exports
- [ ] Header updated to use `useWebSocket` hook
- [ ] LocalStorage persistence works
- [ ] WebSocket connection established on page load
- [ ] Connection status shows in header
- [ ] `tsc --noEmit` passes
- [ ] `npm run lint` passes
- [ ] `npm run build` passes

**Gate: All checks must pass before proceeding to Phase 4.**

---

## Next Steps

After completing Phase 3, you have:

1. **Foundation** - Project setup, types, theming
2. **Libraries** - API client, WebSocket client, utilities
3. **Hooks** - `useWebSocket` and `useChat` for state management

The skeleton pages are in place. Continue to Phase 4+ to implement:

- Layout components (Header fully styled, Sidebar)
- Chat components (ChatWindow, MessageBubble, ToolExecutionCard)
- Diagnostics components (OSILadderViz, ManualToolPanel, ToolCard)
- Analytics components (SummaryCards, SessionsChart, ToolStatsTable)
- Full page implementations

Each phase builds on the previous, with lint/build verification at each step.

