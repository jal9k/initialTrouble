# ChatWindow Component

This document specifies the ChatWindow component, the main container for the chat interface.

## File Location

```
frontend/
  components/
    chat/
      ChatWindow.tsx
```

---

## Overview

The ChatWindow component provides:
- Message list display with auto-scroll
- User input area
- Tool execution display
- Loading/streaming states
- Error handling with retry

This component uses a **headless pattern** by consuming the `useChat` hook.

---

## Headless API

The ChatWindow uses the `useChat` hook for all state management. See [use-chat.md](../../hooks/use-chat.md) for the full headless API.

### Consumed from useChat

```typescript
const {
  // State
  messages,
  isStreaming,
  isEmpty,
  error,
  currentToolExecution,
  
  // Actions
  sendMessage,
  retryLastMessage,
  clearMessages
} = useChat(options)
```

---

## Props Interface

```typescript
interface ChatWindowProps {
  /** Initial conversation ID to load */
  initialConversationId?: string
  
  /** Callback when session starts */
  onSessionStart?: (sessionId: string) => void
  
  /** Callback when session ends */
  onSessionEnd?: (outcome: SessionOutcome) => void
  
  /** Additional CSS classes */
  className?: string
}
```

---

## Component Structure

```
┌─────────────────────────────────────────────────────────────┐
│  ChatWindow                                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Message Area (ScrollArea)                            │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  Empty State / Welcome Message                  │  │  │
│  │  │  OR                                             │  │  │
│  │  │  MessageBubble (user)                           │  │  │
│  │  │  MessageBubble (assistant)                      │  │  │
│  │  │  ToolExecutionCard (if executing)               │  │  │
│  │  │  MessageBubble (user)                           │  │  │
│  │  │  ...                                            │  │  │
│  │  │  Typing Indicator (if streaming)                │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Input Area                                           │  │
│  │  ┌─────────────────────────────────────┐ ┌─────────┐ │  │
│  │  │  Textarea                           │ │  Send   │ │  │
│  │  └─────────────────────────────────────┘ └─────────┘ │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component States

| State | Description | Visual |
|-------|-------------|--------|
| Empty | No messages | Welcome message with suggestions |
| Active | Has messages | Message list displayed |
| Streaming | Awaiting response | Typing indicator shown |
| Tool Executing | Tool running | ToolExecutionCard displayed |
| Error | Send failed | Error message with retry |

---

## Behaviors

### Auto-Scroll
- Scrolls to bottom on new messages
- Preserves scroll position when reading history
- Smooth scroll animation
- "Scroll to bottom" button when scrolled up

### Message Input
- Multi-line textarea
- Submit on Enter (Shift+Enter for newline)
- Disabled during streaming
- Character limit (optional)

### Empty State
- Welcome message
- Suggested prompts/topics
- Quick action buttons

### Error Handling
- Inline error display
- Retry button
- Clear error on new message

---

## shadcn/ui Dependencies

| Component | Usage |
|-----------|-------|
| `ScrollArea` | Scrollable message container |
| `Button` | Send, retry actions |
| `Textarea` | Message input |
| `Card` | Empty state container |

---

## Styling Guidelines

### Layout
```css
.chat-window {
  @apply flex flex-col h-full;
}

.message-area {
  @apply flex-1 overflow-hidden;
}

.input-area {
  @apply border-t p-4 bg-background;
}
```

### Empty State
```css
.empty-state {
  @apply flex flex-col items-center justify-center h-full;
  @apply text-center p-8;
}

.empty-title {
  @apply text-xl font-semibold mb-2;
}

.empty-description {
  @apply text-muted-foreground mb-6;
}

.suggestion-grid {
  @apply grid grid-cols-2 gap-2 max-w-md;
}
```

### Typing Indicator
```css
.typing-indicator {
  @apply flex items-center gap-1 p-2;
}

.typing-dot {
  @apply w-2 h-2 rounded-full bg-muted-foreground;
  @apply animate-bounce;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.1s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.2s;
}
```

---

## Implementation

```typescript
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
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }, [messages, currentToolExecution])

  // Handle scroll position for "scroll to bottom" button
  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    const target = event.target as HTMLDivElement
    const isNearBottom = target.scrollHeight - target.scrollTop - target.clientHeight < 100
    setShowScrollButton(!isNearBottom)
  }, [])

  // Scroll to bottom handler
  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
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
    <div className={cn('flex flex-col h-full', className)}>
      {/* Message Area */}
      <ScrollArea
        ref={scrollAreaRef}
        className="flex-1"
        onScroll={handleScroll}
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
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={retryLastMessage}
                    >
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

## Usage Example (Headless)

To use the chat logic without the default UI:

```typescript
'use client'

import { useChat } from '@/hooks/use-chat'

function CustomChat() {
  const {
    messages,
    isStreaming,
    sendMessage
  } = useChat()

  return (
    <div className="my-custom-layout">
      <MyMessageList messages={messages} />
      {isStreaming && <MyLoadingSpinner />}
      <MyInputForm onSubmit={sendMessage} disabled={isStreaming} />
    </div>
  )
}
```

---

## Accessibility

| Feature | Implementation |
|---------|---------------|
| Live region | New messages announced |
| Focus management | Focus textarea after send |
| Keyboard nav | Enter to send, Shift+Enter for newline |
| Status announcements | Streaming/error states announced |

---

## Test Specifications

### Render Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Empty state shown | Welcome message visible |
| Messages rendered | All messages displayed |
| Suggestions shown | Clickable suggestion buttons |
| Input area visible | Textarea and send button |

### Message Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| User message added | Message appears in list |
| Assistant response shown | Response displayed |
| Tool execution shown | Card appears during execution |
| Typing indicator shown | Dots animate during streaming |

### Interaction Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Send button sends message | Message sent on click |
| Enter sends message | Message sent on Enter |
| Shift+Enter adds newline | No send, newline added |
| Suggestion click sends | Message sent |
| Retry sends last message | Previous message resent |

### Scroll Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Auto-scroll on new message | Scrolls to bottom |
| Scroll button appears | Visible when scrolled up |
| Scroll button scrolls | Smooth scroll to bottom |

### Error Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Error displayed | Error message shown |
| Retry button works | Resends on click |
| Error cleared | Gone after successful send |

---

## Lint/Build Verification

- [ ] Component properly typed
- [ ] Consumes useChat correctly
- [ ] Auto-scroll works
- [ ] All states rendered
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All tests pass

---

## Related Documents

- [use-chat.md](../../hooks/use-chat.md) - Chat state hook
- [MessageBubble.md](./MessageBubble.md) - Message display
- [ToolExecutionCard.md](./ToolExecutionCard.md) - Tool display
- [chat-page.md](../pages/chat-page.md) - Page using this component
- [headless-patterns.md](../../headless-patterns.md) - Headless pattern guide

