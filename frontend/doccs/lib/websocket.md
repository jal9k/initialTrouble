# WebSocket Client

This document specifies the WebSocket client for real-time communication with the Python backend.

## File Location

```
frontend/
  lib/
    websocket.ts    # WebSocket client class
```

---

## Overview

The WebSocket client provides:
- Connection lifecycle management
- Automatic reconnection
- Message serialization/deserialization
- Event-based communication
- Type-safe message handling

---

## Configuration

```typescript
// lib/websocket.ts

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'
const WS_ENDPOINT = '/ws'

interface WebSocketConfig {
  url?: string
  reconnect?: boolean
  reconnectInterval?: number
  maxReconnectAttempts?: number
  onOpen?: () => void
  onClose?: (event: CloseEvent) => void
  onError?: (error: Event) => void
  onMessage?: (message: ServerMessage) => void
}

const DEFAULT_CONFIG: Required<Omit<WebSocketConfig, 'onOpen' | 'onClose' | 'onError' | 'onMessage'>> = {
  url: `${WS_BASE_URL}${WS_ENDPOINT}`,
  reconnect: true,
  reconnectInterval: 3000,
  maxReconnectAttempts: 5
}
```

---

## WebSocket Client Class

```typescript
/**
 * WebSocket client for chat communication
 */
class ChatWebSocket {
  private socket: WebSocket | null = null
  private config: Required<WebSocketConfig>
  private reconnectAttempts = 0
  private reconnectTimeout: NodeJS.Timeout | null = null
  private messageQueue: ClientMessage[] = []
  
  constructor(config: WebSocketConfig = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config } as Required<WebSocketConfig>
  }
  
  /**
   * Current connection state
   */
  get state(): ConnectionState {
    if (!this.socket) return 'disconnected'
    
    switch (this.socket.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting'
      case WebSocket.OPEN:
        return 'connected'
      case WebSocket.CLOSING:
      case WebSocket.CLOSED:
      default:
        return 'disconnected'
    }
  }
  
  /**
   * Whether the socket is connected
   */
  get isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN
  }
  
  /**
   * Connect to the WebSocket server
   */
  connect(): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return
    }
    
    this.socket = new WebSocket(this.config.url)
    
    this.socket.onopen = () => {
      this.reconnectAttempts = 0
      this.flushMessageQueue()
      this.config.onOpen?.()
    }
    
    this.socket.onclose = (event) => {
      this.config.onClose?.(event)
      this.handleReconnect()
    }
    
    this.socket.onerror = (error) => {
      this.config.onError?.(error)
    }
    
    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as ServerMessage
        this.config.onMessage?.(message)
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err)
      }
    }
  }
  
  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }
    
    if (this.socket) {
      this.socket.close(1000, 'Client disconnect')
      this.socket = null
    }
  }
  
  /**
   * Send a message to the server
   */
  send(message: ClientMessage): void {
    if (this.isConnected) {
      this.socket!.send(JSON.stringify(message))
    } else {
      // Queue message for when connection is established
      this.messageQueue.push(message)
      
      // Attempt to connect if not already
      if (this.state === 'disconnected') {
        this.connect()
      }
    }
  }
  
  /**
   * Handle automatic reconnection
   */
  private handleReconnect(): void {
    if (!this.config.reconnect) return
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }
    
    this.reconnectAttempts++
    
    this.reconnectTimeout = setTimeout(() => {
      this.connect()
    }, this.config.reconnectInterval)
  }
  
  /**
   * Send queued messages after reconnection
   */
  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift()!
      this.send(message)
    }
  }
}
```

---

## Event Emitter Pattern (Alternative)

For more flexibility, an event-based pattern:

```typescript
type WebSocketEventType = 'open' | 'close' | 'error' | 'message'

interface WebSocketEvents {
  open: () => void
  close: (event: CloseEvent) => void
  error: (error: Event) => void
  message: (message: ServerMessage) => void
}

class ChatWebSocketEmitter extends ChatWebSocket {
  private listeners = new Map<WebSocketEventType, Set<Function>>()
  
  on<T extends WebSocketEventType>(
    event: T,
    callback: WebSocketEvents[T]
  ): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    
    this.listeners.get(event)!.add(callback)
    
    // Return unsubscribe function
    return () => {
      this.listeners.get(event)?.delete(callback)
    }
  }
  
  private emit<T extends WebSocketEventType>(
    event: T,
    ...args: Parameters<WebSocketEvents[T]>
  ): void {
    this.listeners.get(event)?.forEach(callback => {
      callback(...args)
    })
  }
}
```

---

## Singleton Pattern

For app-wide WebSocket connection:

```typescript
let instance: ChatWebSocket | null = null

function getWebSocket(config?: WebSocketConfig): ChatWebSocket {
  if (!instance) {
    instance = new ChatWebSocket(config)
  }
  return instance
}

function destroyWebSocket(): void {
  if (instance) {
    instance.disconnect()
    instance = null
  }
}
```

---

## Export Pattern

```typescript
// lib/websocket.ts

export { ChatWebSocket, getWebSocket, destroyWebSocket }
export type { WebSocketConfig, ConnectionState }
```

---

## Usage Examples

### Basic Usage

```typescript
import { ChatWebSocket } from '@/lib/websocket'

const ws = new ChatWebSocket({
  onMessage: (message) => {
    console.log('Received:', message)
  },
  onOpen: () => {
    console.log('Connected!')
  }
})

ws.connect()

// Send a message
ws.send({
  message: 'Hello, how can I fix my network?',
  conversation_id: 'abc-123'
})

// Cleanup
ws.disconnect()
```

### With React Hook

```typescript
'use client'

import { useEffect, useRef } from 'react'
import { ChatWebSocket } from '@/lib/websocket'

function useChatWebSocket(options: WebSocketConfig) {
  const wsRef = useRef<ChatWebSocket | null>(null)
  
  useEffect(() => {
    wsRef.current = new ChatWebSocket(options)
    wsRef.current.connect()
    
    return () => {
      wsRef.current?.disconnect()
    }
  }, [])
  
  return wsRef.current
}
```

### With Streaming Response

```typescript
const ws = new ChatWebSocket({
  onMessage: (message) => {
    // Handle streaming tokens
    if (message.response) {
      appendToCurrentMessage(message.response)
    }
    
    // Handle tool calls
    if (message.tool_calls) {
      showToolExecution(message.tool_calls)
    }
  }
})
```

---

## Connection States

```
┌──────────────┐
│ disconnected │ ◄─────────────────────┐
└──────┬───────┘                       │
       │ connect()                     │
       ▼                               │
┌──────────────┐                       │
│  connecting  │                       │
└──────┬───────┘                       │
       │ onopen                        │
       ▼                               │
┌──────────────┐     onerror/onclose   │
│  connected   │ ──────────────────────┤
└──────┬───────┘                       │
       │ disconnect()                  │
       ▼                               │
┌──────────────┐     reconnect         │
│   closing    │ ──────────────────────┘
└──────────────┘
```

---

## Error Handling

| Error Type | Handling Strategy |
|------------|-------------------|
| Connection refused | Automatic reconnect with backoff |
| Network error | Queue messages, reconnect |
| Parse error | Log error, continue |
| Server close | Check close code, may reconnect |

### Close Codes

| Code | Meaning | Action |
|------|---------|--------|
| 1000 | Normal closure | Don't reconnect |
| 1001 | Going away | Reconnect |
| 1006 | Abnormal closure | Reconnect with backoff |
| 1011 | Server error | Reconnect after delay |

---

## Test Specifications

### Unit Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Constructor sets defaults | Config merged with defaults |
| `connect()` creates WebSocket | Socket instance created |
| `disconnect()` closes socket | Socket closed with code 1000 |
| `send()` serializes message | JSON string sent |
| `send()` queues when disconnected | Message added to queue |
| Queue flushed on connect | All queued messages sent |

### Connection Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Auto-reconnect on disconnect | Reconnects after interval |
| Max reconnect attempts | Stops after max attempts |
| State updates correctly | State reflects socket readyState |

### Message Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Valid JSON parsed | onMessage called with parsed data |
| Invalid JSON logged | Error logged, no crash |
| Message callback invoked | Callback receives ServerMessage |

### Integration Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Full conversation flow | Messages sent and received |
| Tool calls received | tool_calls array populated |
| Conversation ID persisted | Same ID across messages |

---

## Lint/Build Verification

- [ ] Class properly typed
- [ ] All states handled
- [ ] No memory leaks (cleanup on disconnect)
- [ ] Event handlers typed
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] Unit tests pass

---

## Related Documents

- [interfaces.md](../types/interfaces.md) - Message types
- [use-websocket.md](../hooks/use-websocket.md) - React hook wrapper
- [api.md](./api.md) - REST API client

