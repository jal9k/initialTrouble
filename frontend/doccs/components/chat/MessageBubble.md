# MessageBubble Component

This document specifies the MessageBubble component for displaying chat messages.

## File Location

```
frontend/
  components/
    chat/
      MessageBubble.tsx
```

---

## Overview

The MessageBubble component displays a single chat message with:
- Role-based styling (user/assistant/system/tool)
- Markdown rendering for assistant messages
- Tool call indicators
- Timestamps
- Copy functionality

---

## Props Interface

```typescript
interface MessageBubbleProps {
  /** The message to display */
  message: Message
  
  /** Whether this is the latest message (for animations) */
  isLatest?: boolean
  
  /** Whether to show timestamp */
  showTimestamp?: boolean
  
  /** Additional CSS classes */
  className?: string
}
```

---

## Component Structure

```
┌─────────────────────────────────────────────────────────────┐
│  MessageBubble (User)                                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                                        ┌────────────┐ │  │
│  │                                        │  Message   │ │  │
│  │                                        │  Content   │ │  │
│  │                                        └────────────┘ │  │
│  │                                           12:34 PM    │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  MessageBubble (Assistant)                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ┌────────────────────────────────────────────────┐    │  │
│  │ │  Message Content                               │    │  │
│  │ │  (Markdown rendered)                           │    │  │
│  │ │  - Lists                                       │    │  │
│  │ │  - Code blocks                                 │    │  │
│  │ └────────────────────────────────────────────────┘    │  │
│  │ 12:34 PM                                 [Copy]       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  MessageBubble (Tool Result)                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ⚡ ping_gateway                                       │  │
│  │ ┌────────────────────────────────────────────────┐    │  │
│  │ │  Result output...                              │    │  │
│  │ └────────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component States

| State | Description | Visual |
|-------|-------------|--------|
| User Message | User's input | Right-aligned, accent background |
| Assistant Message | AI response | Left-aligned, muted background |
| System Message | System info | Center-aligned, subtle styling |
| Tool Message | Tool result | Left-aligned, code-like styling |
| Latest | Most recent | Entry animation |

---

## Behaviors

### Markdown Rendering
- Assistant messages rendered as Markdown
- Syntax highlighting for code blocks
- Links open in new tab
- Images rendered inline (if allowed)

### Copy Functionality
- Copy button on hover (assistant messages)
- Copies raw markdown content
- Shows confirmation toast

### Timestamps
- Shown by default on assistant messages
- Optional on user messages
- Relative time for recent, absolute for older

---

## shadcn/ui Dependencies

| Component | Usage |
|-----------|-------|
| `Button` | Copy action |
| `Tooltip` | Copy button label |
| `Separator` | Dividing sections |

### External Dependencies

| Package | Usage |
|---------|-------|
| `react-markdown` | Markdown rendering |
| `remark-gfm` | GitHub Flavored Markdown |
| `rehype-highlight` | Syntax highlighting |

---

## Styling Guidelines

### Role-Based Styling
```css
/* User messages */
.message-user {
  @apply ml-auto max-w-[80%];
  @apply bg-primary text-primary-foreground;
  @apply rounded-2xl rounded-br-md;
}

/* Assistant messages */
.message-assistant {
  @apply mr-auto max-w-[80%];
  @apply bg-muted;
  @apply rounded-2xl rounded-bl-md;
}

/* System messages */
.message-system {
  @apply mx-auto max-w-[90%];
  @apply text-muted-foreground text-sm text-center;
  @apply italic;
}

/* Tool result messages */
.message-tool {
  @apply mr-auto max-w-[90%];
  @apply bg-muted/50 border;
  @apply rounded-lg font-mono text-sm;
}
```

### Markdown Content
```css
.markdown-content {
  @apply prose prose-sm dark:prose-invert;
  @apply max-w-none;
}

.markdown-content pre {
  @apply bg-muted rounded-md p-3 overflow-x-auto;
}

.markdown-content code {
  @apply bg-muted px-1 py-0.5 rounded text-sm;
}

.markdown-content a {
  @apply text-primary underline;
}
```

### Animation
```css
.message-enter {
  @apply animate-in fade-in slide-in-from-bottom-2;
  @apply duration-200;
}
```

---

## Implementation

```typescript
'use client'

import { useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn, formatDate } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Check, Copy, Zap } from 'lucide-react'
import type { Message } from '@/types'

const roleStyles: Record<string, string> = {
  user: 'ml-auto bg-primary text-primary-foreground rounded-2xl rounded-br-md',
  assistant: 'mr-auto bg-muted rounded-2xl rounded-bl-md',
  system: 'mx-auto text-muted-foreground text-sm text-center italic',
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
        className={cn(
          'px-4 py-2 max-w-[80%]',
          roleStyles[message.role]
        )}
      >
        {shouldRenderMarkdown ? (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            className="prose prose-sm dark:prose-invert max-w-none"
            components={{
              a: ({ href, children }) => (
                <a href={href} target="_blank" rel="noopener noreferrer">
                  {children}
                </a>
              ),
              code: ({ inline, className, children }) => {
                if (inline) {
                  return (
                    <code className="bg-muted px-1 py-0.5 rounded text-sm">
                      {children}
                    </code>
                  )
                }
                return (
                  <pre className="bg-muted rounded-md p-3 overflow-x-auto">
                    <code className={className}>{children}</code>
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
            <TooltipContent>
              {copied ? 'Copied!' : 'Copy message'}
            </TooltipContent>
          </Tooltip>
        )}
      </div>

      {/* Tool calls indicator */}
      {message.toolCalls && message.toolCalls.length > 0 && (
        <div className="mt-2 text-xs text-muted-foreground">
          Used: {message.toolCalls.map(tc => tc.name).join(', ')}
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
| Semantic structure | Messages use appropriate heading levels |
| Screen reader | Role announced (user, assistant) |
| Keyboard copy | Copy button keyboard accessible |
| Color contrast | Text meets WCAG AA contrast |

---

## Test Specifications

### Render Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| User message styled correctly | Right-aligned, accent color |
| Assistant message styled correctly | Left-aligned, muted color |
| System message styled correctly | Centered, subtle |
| Tool message shows name | Tool name displayed |
| Timestamp displayed | Time shown when enabled |

### Markdown Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Renders plain text | Text displayed |
| Renders bold/italic | Formatting applied |
| Renders code blocks | Syntax highlighted |
| Renders lists | Bullets/numbers shown |
| Renders links | Clickable, opens new tab |

### Interaction Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Copy button appears on hover | Visible on mouse enter |
| Copy copies content | Content in clipboard |
| Copy shows confirmation | Check icon displayed |

### Animation Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Latest message animates | Fade/slide in animation |
| Non-latest no animation | No entry animation |

---

## Lint/Build Verification

- [ ] Component properly typed
- [ ] Markdown renders safely (no XSS)
- [ ] All role styles defined
- [ ] Animations performant
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All tests pass

---

## Related Documents

- [ChatWindow.md](./ChatWindow.md) - Parent component
- [ToolExecutionCard.md](./ToolExecutionCard.md) - Tool result display
- [interfaces.md](../../types/interfaces.md) - Message type

