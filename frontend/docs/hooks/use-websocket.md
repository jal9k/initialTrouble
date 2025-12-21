# useWebSocket Hook

This document specifies the `useWebSocket` hook, a headless React hook for managing WebSocket connections.

## File Location

```
frontend/
  hooks/
    use-websocket.ts    # WebSocket hook
```

---

## Overview

The `useWebSocket` hook provides a React-friendly wrapper around the WebSocket client, with:
- Automatic connection lifecycle management
- React state for connection status
- Cleanup on unmount
- Reconnection handling
- Message queue for offline sending

---

## Headless API

### Hook Interface

```typescript
interface UseWebSocketOptions {
  /** WebSocket server URL (defaults to env variable) */
  url?: string
  
  /** Auto-connect on mount (default: true) */
  autoConnect?: boolean
  
  /** Enable auto-reconnect (default: true) */
  reconnect?: boolean
  
  /** Reconnect interval in ms (default: 3000) */
  reconnectInterval?: number
  
  /** Max reconnect attempts (default: 5) */
  maxReconnectAttempts?: number
  
  /** Callback when message received */
  onMessage?: (message: ServerMessage) => void
  
  /** Callback when connection opens */
  onOpen?: () => void
  
  /** Callback when connection closes */
  onClose?: (event: CloseEvent) => void
  
  /** Callback when error occurs */
  onError?: (error: Event) => void
}

interface UseWebSocketReturn {
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
```

### Returned State

| Property | Type | Description |
|----------|------|-------------|
| `isConnected` | `boolean` | Whether socket is open and ready |
| `isConnecting` | `boolean` | Whether connection is in progress |
| `connectionState` | `ConnectionState` | Full connection state |
| `error` | `WebSocketError \| null` | Last error that occurred |
| `lastMessage` | `ServerMessage \| null` | Most recent message received |

### Returned Derived State

| Property | Type | Description |
|----------|------|-------------|
| `canSend` | `boolean` | Whether messages can be sent (connected) |
| `reconnectAttempts` | `number` | Number of reconnection attempts made |

### Returned Actions

| Action | Signature | Description |
|--------|-----------|-------------|
| `connect` | `() => void` | Initiate WebSocket connection |
| `disconnect` | `() => void` | Close WebSocket connection |
| `send` | `(message: ClientMessage) => void` | Send message (queued if disconnected) |

---

## Implementation

```typescript
'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { ChatWebSocket } from '@/lib/websocket'
import type {
  ConnectionState,
  ServerMessage,
  ClientMessage,
  WebSocketError
} from '@/types'

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

## Usage Example (Headless)

### With Custom UI

```typescript
'use client'

import { useWebSocket } from '@/hooks/use-websocket'

function CustomConnectionStatus() {
  const {
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect
  } = useWebSocket({
    autoConnect: false
  })

  return (
    <div className="flex items-center gap-2">
      <div
        className={cn(
          'w-2 h-2 rounded-full',
          isConnected && 'bg-green-500',
          isConnecting && 'bg-yellow-500 animate-pulse',
          !isConnected && !isConnecting && 'bg-red-500'
        )}
      />
      
      <span>
        {isConnected ? 'Connected' : isConnecting ? 'Connecting...' : 'Disconnected'}
      </span>
      
      {error && <span className="text-red-500 text-sm">{error.reason}</span>}
      
      <button onClick={isConnected ? disconnect : connect}>
        {isConnected ? 'Disconnect' : 'Connect'}
      </button>
    </div>
  )
}
```

### With Message Handling

```typescript
'use client'

import { useState, useCallback } from 'react'
import { useWebSocket } from '@/hooks/use-websocket'

function ChatClient() {
  const [messages, setMessages] = useState<ServerMessage[]>([])
  
  const handleMessage = useCallback((message: ServerMessage) => {
    setMessages(prev => [...prev, message])
  }, [])
  
  const { send, isConnected } = useWebSocket({
    onMessage: handleMessage
  })
  
  const sendMessage = (text: string) => {
    send({ message: text })
  }
  
  return (
    <div>
      <div className="messages">
        {messages.map((msg, i) => (
          <div key={i}>{msg.response}</div>
        ))}
      </div>
      <input
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            sendMessage(e.currentTarget.value)
            e.currentTarget.value = ''
          }
        }}
        disabled={!isConnected}
      />
    </div>
  )
}
```

---

## Default Styled Component

For convenience, a pre-styled connection indicator:

```typescript
'use client'

import { useWebSocket } from '@/hooks/use-websocket'
import { cn } from '@/lib/utils'

interface ConnectionIndicatorProps {
  className?: string
}

export function ConnectionIndicator({ className }: ConnectionIndicatorProps) {
  const { isConnected, isConnecting, error } = useWebSocket()
  
  return (
    <div className={cn('flex items-center gap-2 text-sm', className)}>
      <span
        className={cn(
          'w-2 h-2 rounded-full',
          isConnected && 'bg-green-500',
          isConnecting && 'bg-yellow-500 animate-pulse',
          error && 'bg-red-500',
          !isConnected && !isConnecting && !error && 'bg-gray-400'
        )}
        aria-hidden="true"
      />
      <span className="sr-only">
        {isConnected ? 'Connected' : isConnecting ? 'Connecting' : 'Disconnected'}
      </span>
    </div>
  )
}
```

---

## State Diagram

```
                    ┌──────────────────┐
                    │   disconnected   │
                    └────────┬─────────┘
                             │ connect()
                             ▼
                    ┌──────────────────┐
                    │   connecting     │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              │              ▼
     ┌────────────────┐      │     ┌────────────────┐
     │    connected   │◄─────┘     │     error      │
     └────────┬───────┘            └────────┬───────┘
              │ disconnect()                │
              │ or close event              │ auto-reconnect
              ▼                             │
     ┌────────────────┐                     │
     │  disconnected  │◄────────────────────┘
     └────────────────┘
```

---

## Test Specifications

### Hook State Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Initial state is disconnected | `connectionState === 'disconnected'` |
| autoConnect triggers connection | State becomes 'connecting' on mount |
| Manual connect changes state | State becomes 'connecting' |
| Successful connection | `isConnected === true` |
| Error sets error state | `error` is populated |

### Action Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| `connect()` initiates connection | WebSocket.connect() called |
| `disconnect()` closes connection | WebSocket.disconnect() called |
| `send()` sends message | Message serialized and sent |
| `send()` queues when disconnected | Message queued for later |

### Callback Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| `onMessage` called on message | Callback receives ServerMessage |
| `onOpen` called on connect | Callback invoked |
| `onClose` called on disconnect | Callback receives CloseEvent |
| `onError` called on error | Callback receives Error |

### Lifecycle Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Cleanup on unmount | Connection closed |
| Reconnect on disconnect | Attempts reconnection |
| Max attempts respected | Stops after max attempts |

### Integration Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Full send/receive cycle | Message sent and response received |
| Multiple components share state | Singleton pattern works |
| Hot reload preserves connection | Connection survives HMR |

---

## Lint/Build Verification

- [ ] Hook properly typed
- [ ] All options have defaults
- [ ] Cleanup implemented
- [ ] No memory leaks
- [ ] Stable action references (useCallback)
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All tests pass

---

## Related Documents

- [websocket.md](../lib/websocket.md) - Underlying WebSocket client
- [use-chat.md](./use-chat.md) - Chat hook that uses this hook
- [headless-patterns.md](../headless-patterns.md) - Headless architecture guide
- [interfaces.md](../types/interfaces.md) - Type definitions

