# useChat Hook

This document specifies the `useChat` hook, a headless React hook for managing chat state and conversation flow.

## File Location

```
frontend/
  hooks/
    use-chat.ts    # Chat state hook
```

---

## Overview

The `useChat` hook provides complete chat state management:
- Message list management
- Conversation persistence
- Streaming response handling
- Tool execution tracking
- Session lifecycle

This is the primary hook for the chat interface.

---

## Headless API

### Hook Interface

```typescript
interface UseChatOptions {
  /** Initial conversation ID to load */
  initialConversationId?: string
  
  /** Callback when session starts */
  onSessionStart?: (conversationId: string) => void
  
  /** Callback when session ends */
  onSessionEnd?: (outcome: SessionOutcome) => void
  
  /** Callback when message received */
  onMessage?: (message: Message) => void
  
  /** Callback when tool execution starts */
  onToolStart?: (toolCall: ToolCall) => void
  
  /** Callback when tool execution completes */
  onToolComplete?: (result: ToolResult) => void
  
  /** Enable local storage persistence (default: true) */
  persist?: boolean
}

interface UseChatReturn {
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
```

### Returned State

| Property | Type | Description |
|----------|------|-------------|
| `messages` | `Message[]` | All messages in conversation |
| `conversationId` | `string \| null` | Current conversation ID |
| `isStreaming` | `boolean` | Whether response is streaming |
| `isLoading` | `boolean` | Whether loading conversation |
| `error` | `Error \| null` | Last error that occurred |
| `currentToolExecution` | `ToolCall \| null` | Currently executing tool |

### Returned Derived State

| Property | Type | Description |
|----------|------|-------------|
| `isEmpty` | `boolean` | No messages in conversation |
| `lastMessage` | `Message \| null` | Most recent message |
| `lastUserMessage` | `Message \| null` | Most recent user message |
| `lastAssistantMessage` | `Message \| null` | Most recent assistant message |
| `messageCount` | `number` | Total message count |
| `toolsUsed` | `string[]` | Unique tool names used |

### Returned Actions

| Action | Signature | Description |
|--------|-----------|-------------|
| `sendMessage` | `(content: string) => Promise<void>` | Send user message |
| `clearMessages` | `() => void` | Clear all messages |
| `loadConversation` | `(id: string) => Promise<void>` | Load existing conversation |
| `startNewConversation` | `() => void` | Start fresh conversation |
| `endConversation` | `(outcome: SessionOutcome) => void` | End and save conversation |
| `retryLastMessage` | `() => Promise<void>` | Retry last user message |

---

## Implementation

```typescript
'use client'

import { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import { useWebSocket } from './use-websocket'
import { getSessionMessages } from '@/lib/api'
import { generateId } from '@/lib/utils'
import type {
  Message,
  MessageRole,
  ToolCall,
  ToolResult,
  ServerMessage,
  SessionOutcome
} from '@/types'

const STORAGE_KEY = 'chat_messages'

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
  const callbacksRef = useRef({ onSessionStart, onSessionEnd, onMessage, onToolStart, onToolComplete })

  // Update callbacks ref
  useEffect(() => {
    callbacksRef.current = { onSessionStart, onSessionEnd, onMessage, onToolStart, onToolComplete }
  }, [onSessionStart, onSessionEnd, onMessage, onToolStart, onToolComplete])

  // Handle incoming WebSocket messages
  const handleWebSocketMessage = useCallback((serverMessage: ServerMessage) => {
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

      setMessages(prev => [...prev, assistantMessage])
      callbacksRef.current.onMessage?.(assistantMessage)

      // Handle tool results
      if (serverMessage.tool_calls?.length) {
        serverMessage.tool_calls.forEach(tc => {
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
  }, [conversationId])

  // WebSocket connection
  const { send, isConnected } = useWebSocket({
    onMessage: handleWebSocketMessage
  })

  // Load from localStorage on mount
  useEffect(() => {
    if (persist && !initialConversationId) {
      try {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (stored) {
          const parsed = JSON.parse(stored)
          setMessages(parsed.messages || [])
          setConversationId(parsed.conversationId || null)
        }
      } catch {
        // Ignore parse errors
      }
    }
  }, [persist, initialConversationId])

  // Save to localStorage on message changes
  useEffect(() => {
    if (persist && messages.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        messages,
        conversationId
      }))
    }
  }, [persist, messages, conversationId])

  // Actions
  const sendMessage = useCallback(async (content: string) => {
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

    setMessages(prev => [...prev, userMessage])
    pendingMessageRef.current = content.trim()

    // Send via WebSocket
    send({
      message: content.trim(),
      conversation_id: conversationId || undefined
    })
  }, [conversationId, send])

  const clearMessages = useCallback(() => {
    setMessages([])
    setConversationId(null)
    setError(null)
    setCurrentToolExecution(null)
    if (persist) {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [persist])

  const loadConversation = useCallback(async (id: string) => {
    setIsLoading(true)
    setError(null)

    try {
      const loadedMessages = await getSessionMessages(id)
      setMessages(loadedMessages)
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

  const endConversation = useCallback((outcome: SessionOutcome) => {
    callbacksRef.current.onSessionEnd?.(outcome)
    // Could also call API to save session outcome
  }, [])

  const retryLastMessage = useCallback(async () => {
    if (pendingMessageRef.current) {
      // Remove last assistant message if it exists
      setMessages(prev => {
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
    () => [...messages].reverse().find(m => m.role === 'user') || null,
    [messages]
  )
  const lastAssistantMessage = useMemo(
    () => [...messages].reverse().find(m => m.role === 'assistant') || null,
    [messages]
  )
  const messageCount = messages.length
  const toolsUsed = useMemo(() => {
    const tools = new Set<string>()
    messages.forEach(msg => {
      msg.toolCalls?.forEach(tc => tools.add(tc.name))
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

## Usage Example (Headless)

### With Custom UI

```typescript
'use client'

import { useChat } from '@/hooks/use-chat'

function MinimalChat() {
  const {
    messages,
    isStreaming,
    isEmpty,
    sendMessage
  } = useChat()

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = e.currentTarget
    const input = form.elements.namedItem('message') as HTMLInputElement
    sendMessage(input.value)
    input.value = ''
  }

  return (
    <div>
      {isEmpty ? (
        <p>Start a conversation...</p>
      ) : (
        <ul>
          {messages.map(msg => (
            <li key={msg.id} data-role={msg.role}>
              {msg.content}
            </li>
          ))}
        </ul>
      )}
      
      <form onSubmit={handleSubmit}>
        <input name="message" disabled={isStreaming} />
        <button type="submit" disabled={isStreaming}>
          Send
        </button>
      </form>
    </div>
  )
}
```

### With Tool Execution Display

```typescript
'use client'

import { useChat } from '@/hooks/use-chat'
import { ToolExecutionCard } from '@/components/chat/ToolExecutionCard'

function ChatWithTools() {
  const {
    messages,
    currentToolExecution,
    isStreaming,
    sendMessage,
    toolsUsed
  } = useChat({
    onToolStart: (tool) => console.log('Tool started:', tool.name),
    onToolComplete: (result) => console.log('Tool completed:', result)
  })

  return (
    <div>
      <div className="messages">
        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        
        {currentToolExecution && (
          <ToolExecutionCard
            execution={{
              toolName: currentToolExecution.name,
              status: 'executing'
            }}
          />
        )}
      </div>
      
      <div className="tools-used">
        Tools used: {toolsUsed.join(', ') || 'None'}
      </div>
      
      <ChatInput onSubmit={sendMessage} disabled={isStreaming} />
    </div>
  )
}
```

### With Session Management

```typescript
'use client'

import { useChat } from '@/hooks/use-chat'

function SessionAwareChat() {
  const {
    conversationId,
    loadConversation,
    startNewConversation,
    endConversation,
    messageCount
  } = useChat({
    onSessionStart: (id) => {
      // Update URL with session ID
      window.history.replaceState({}, '', `/chat/${id}`)
    },
    onSessionEnd: (outcome) => {
      console.log(`Session ended: ${outcome}`)
    }
  })

  return (
    <div>
      <header>
        <span>Session: {conversationId || 'New'}</span>
        <span>Messages: {messageCount}</span>
        <button onClick={startNewConversation}>New Chat</button>
        <button onClick={() => endConversation('resolved')}>
          Mark Resolved
        </button>
      </header>
      {/* Chat UI */}
    </div>
  )
}
```

---

## Default Styled Component

For convenience, a pre-styled chat container:

```typescript
'use client'

import { useChat, UseChatOptions } from '@/hooks/use-chat'
import { MessageBubble } from '@/components/chat/MessageBubble'
import { ToolExecutionCard } from '@/components/chat/ToolExecutionCard'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

interface ChatContainerProps extends UseChatOptions {
  className?: string
}

export function ChatContainer({ className, ...options }: ChatContainerProps) {
  const {
    messages,
    isStreaming,
    isEmpty,
    currentToolExecution,
    error,
    sendMessage,
    retryLastMessage
  } = useChat(options)

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = e.currentTarget
    const input = form.elements.namedItem('message') as HTMLInputElement
    if (input.value.trim()) {
      sendMessage(input.value)
      input.value = ''
    }
  }

  return (
    <div className={cn('flex flex-col h-full', className)}>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isEmpty ? (
          <div className="text-center text-muted-foreground py-8">
            How can I help with your network issues?
          </div>
        ) : (
          messages.map(msg => (
            <MessageBubble key={msg.id} message={msg} />
          ))
        )}
        
        {currentToolExecution && (
          <ToolExecutionCard
            execution={{
              toolName: currentToolExecution.name,
              status: 'executing'
            }}
          />
        )}
        
        {isStreaming && !currentToolExecution && (
          <div className="animate-pulse text-muted-foreground">
            Thinking...
          </div>
        )}
        
        {error && (
          <div className="text-destructive flex items-center gap-2">
            <span>{error.message}</span>
            <Button variant="ghost" size="sm" onClick={retryLastMessage}>
              Retry
            </Button>
          </div>
        )}
      </div>
      
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <Input
            name="message"
            placeholder="Describe your network issue..."
            disabled={isStreaming}
            className="flex-1"
          />
          <Button type="submit" disabled={isStreaming}>
            Send
          </Button>
        </div>
      </form>
    </div>
  )
}
```

---

## State Machine

```
                        ┌─────────────────────────────────────┐
                        │             IDLE                    │
                        │  isEmpty: true, isStreaming: false  │
                        └───────────────┬─────────────────────┘
                                        │ sendMessage()
                                        ▼
                        ┌─────────────────────────────────────┐
                        │           SENDING                   │
                        │  isStreaming: true                  │
                        └───────────────┬─────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
     ┌──────────────────────┐ ┌─────────────────┐ ┌─────────────────┐
     │   TOOL_EXECUTING     │ │   RECEIVING     │ │     ERROR       │
     │ currentToolExecution │ │ message arrives │ │ error is set    │
     └──────────┬───────────┘ └────────┬────────┘ └────────┬────────┘
                │                      │                   │
                └──────────────────────┴───────────────────┘
                                       │
                                       ▼
                        ┌─────────────────────────────────────┐
                        │            READY                    │
                        │  isEmpty: false, isStreaming: false │
                        └─────────────────────────────────────┘
```

---

## Test Specifications

### State Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Initial state is empty | `isEmpty === true`, `messages === []` |
| Message added on send | New message in `messages` array |
| isStreaming during send | `isStreaming === true` while waiting |
| Tool execution tracked | `currentToolExecution` populated |

### Action Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| `sendMessage` adds user message | Message with role 'user' added |
| `sendMessage` sends via WebSocket | WebSocket.send() called |
| `clearMessages` resets state | All state reset to initial |
| `loadConversation` fetches messages | API called, messages populated |
| `retryLastMessage` resends | Last user message resent |

### Derived State Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| `isEmpty` accurate | True when no messages |
| `lastMessage` updated | Returns most recent message |
| `toolsUsed` aggregates | Unique tool names collected |

### Persistence Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Messages saved to localStorage | Data persisted on change |
| Messages loaded on mount | Previous session restored |
| Clear removes from storage | localStorage cleared |

### Integration Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Full conversation flow | Send, receive, display cycle |
| Tool execution flow | Tool call received, displayed, completed |
| Session lifecycle | Start, continue, end session |

---

## Lint/Build Verification

- [ ] Hook properly typed
- [ ] All options documented
- [ ] Callbacks use refs (no stale closures)
- [ ] Derived state memoized
- [ ] Actions use useCallback
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All tests pass

---

## Related Documents

- [use-websocket.md](./use-websocket.md) - Underlying WebSocket hook
- [ChatWindow.md](../components/chat/ChatWindow.md) - Main chat component
- [MessageBubble.md](../components/chat/MessageBubble.md) - Message display
- [ToolExecutionCard.md](../components/chat/ToolExecutionCard.md) - Tool display
- [headless-patterns.md](../headless-patterns.md) - Headless architecture guide

