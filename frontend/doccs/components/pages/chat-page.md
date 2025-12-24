# Chat Page

This document specifies the Chat page (`/chat`), the main troubleshooting interface.

## File Location

```
frontend/
  app/
    chat/
      page.tsx
```

---

## Overview

The Chat page provides:
- Three-column layout
- AI-powered chat interface
- OSI layer visualization
- Manual tool execution panel
- Session sidebar

---

## Page Structure

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Header                                                                         │
├──────────────┬─────────────────────────────────────────────────┬───────────────┤
│  Sidebar     │  Main Chat Area                                 │  Right Panel  │
│              │                                                 │               │
│  [+ New]     │  ┌───────────────────────────────────────────┐ │  OSI Ladder   │
│              │  │                                           │ │  ┌─────────┐  │
│  Session 1   │  │  Message bubbles                          │ │  │ 5 │ ○   │  │
│  Session 2   │  │  Tool execution cards                     │ │  │ 4 │ ○   │  │
│  Session 3   │  │  Typing indicators                        │ │  │ 3 │ ◉   │  │
│  ...         │  │                                           │ │  │ 2 │ ✓   │  │
│              │  │                                           │ │  │ 1 │ ✓   │  │
│              │  └───────────────────────────────────────────┘ │  └─────────┘  │
│              │  ┌───────────────────────────────────────────┐ │               │
│              │  │  [Input area                    ] [Send]  │ │  Manual Tools │
│              │  └───────────────────────────────────────────┘ │  ┌─────────┐  │
│              │                                                 │  │ Tool 1  │  │
│              │                                                 │  │ Tool 2  │  │
│              │                                                 │  │ ...     │  │
│              │                                                 │  └─────────┘  │
└──────────────┴─────────────────────────────────────────────────┴───────────────┘
```

---

## Responsive Behavior

| Breakpoint | Layout |
|------------|--------|
| Desktop (lg+) | Three columns: sidebar + chat + right panel |
| Tablet (md) | Two columns: chat + right panel, sidebar as sheet |
| Mobile (sm) | Single column: chat only, panels as sheets |

---

## Data Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            Chat Page                                      │
│                                                                          │
│  ┌─────────────────────┐    ┌─────────────────────┐                     │
│  │     useChat()       │◄──►│   useWebSocket()    │◄──► Python Backend  │
│  │                     │    │                     │     (WebSocket)     │
│  │  - messages         │    │  - isConnected      │                     │
│  │  - sendMessage      │    │  - send()           │                     │
│  │  - currentTool      │    └─────────────────────┘                     │
│  └──────────┬──────────┘                                                │
│             │                                                            │
│             ▼                                                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                         Page Layout                               │   │
│  │  ┌──────────┐  ┌───────────────────┐  ┌───────────────────────┐  │   │
│  │  │ Sidebar  │  │   ChatWindow      │  │   Right Panel         │  │   │
│  │  │          │  │   - messages      │  │   - OSILadderViz      │  │   │
│  │  │          │  │   - input         │  │   - ManualToolPanel   │  │   │
│  │  └──────────┘  └───────────────────┘  └───────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation

```typescript
// app/chat/page.tsx

import { Suspense } from 'react'
import { ChatPageClient } from './client'
import { listSessions, listTools } from '@/lib/api'

export const metadata = {
  title: 'Chat - TechTime',
  description: 'AI-powered network troubleshooting'
}

export default async function ChatPage() {
  // Fetch initial data on server
  const [sessionsResult, toolsResult] = await Promise.all([
    listSessions({ pageSize: 20 }),
    listTools()
  ])

  return (
    <ChatPageClient
      initialSessions={sessionsResult.items}
      tools={toolsResult}
    />
  )
}
```

```typescript
// app/chat/client.tsx
'use client'

import { useState, useCallback } from 'react'
import { useChat } from '@/hooks/use-chat'
import { useOSILadder } from '@/hooks/use-osi-ladder'
import { useManualToolPanel } from '@/hooks/use-manual-tool-panel'
import { cn } from '@/lib/utils'
import { Sidebar } from '@/components/layout/Sidebar'
import { MobileSidebar } from '@/components/layout/MobileSidebar'
import { ChatWindow } from '@/components/chat/ChatWindow'
import { OSILadderViz } from '@/components/diagnostics/OSILadderViz'
import { ManualToolPanel } from '@/components/diagnostics/ManualToolPanel'
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle
} from '@/components/ui/resizable'
import type { SessionListItem, DiagnosticTool } from '@/types'

interface ChatPageClientProps {
  initialSessions: SessionListItem[]
  tools: DiagnosticTool[]
}

export function ChatPageClient({
  initialSessions,
  tools
}: ChatPageClientProps) {
  const [sessions, setSessions] = useState(initialSessions)
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)

  // Chat state
  const chat = useChat({
    onSessionStart: (id) => {
      setActiveSessionId(id)
      // Add to sessions list
      setSessions(prev => [{
        id,
        startTime: new Date(),
        outcome: 'in_progress',
        preview: 'New conversation...'
      }, ...prev])
    }
  })

  // OSI ladder state
  const osiLadder = useOSILadder({
    onLayerChange: (layer, status) => {
      console.log(`Layer ${layer} is now ${status}`)
    }
  })

  // Manual tool panel state
  const toolPanel = useManualToolPanel({
    tools,
    onExecutionComplete: (result) => {
      // Update OSI ladder based on tool result
      const tool = tools.find(t => t.name === result.name)
      if (tool) {
        if (result.error) {
          osiLadder.failLayer(tool.osiLayer, result.error)
        } else {
          osiLadder.passLayer(tool.osiLayer, JSON.stringify(result.result))
        }
      }
    }
  })

  const handleSessionSelect = useCallback((sessionId: string) => {
    setActiveSessionId(sessionId)
    chat.loadConversation(sessionId)
  }, [chat])

  const handleNewSession = useCallback(() => {
    chat.startNewConversation()
    osiLadder.reset()
    setActiveSessionId(null)
  }, [chat, osiLadder])

  return (
    <div className="h-[calc(100vh-56px)]">
      {/* Mobile sidebar trigger in header area */}
      <div className="md:hidden p-2 border-b">
        <MobileSidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSessionSelect={handleSessionSelect}
          onNewSession={handleNewSession}
        />
      </div>

      <ResizablePanelGroup direction="horizontal" className="h-full">
        {/* Sidebar - Desktop only */}
        <ResizablePanel
          defaultSize={20}
          minSize={15}
          maxSize={30}
          className="hidden md:block"
        >
          <Sidebar
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSessionSelect={handleSessionSelect}
            onNewSession={handleNewSession}
          />
        </ResizablePanel>

        <ResizableHandle className="hidden md:flex" />

        {/* Main Chat */}
        <ResizablePanel defaultSize={55} minSize={40}>
          <ChatWindow
            initialConversationId={activeSessionId}
            onSessionStart={chat.onSessionStart}
            onSessionEnd={chat.onSessionEnd}
          />
        </ResizablePanel>

        <ResizableHandle className="hidden lg:flex" />

        {/* Right Panel - Large screens only */}
        <ResizablePanel
          defaultSize={25}
          minSize={20}
          maxSize={35}
          className="hidden lg:block"
        >
          <div className="flex flex-col h-full">
            {/* OSI Ladder */}
            <div className="p-4 border-b">
              <h3 className="font-semibold text-sm mb-3">Diagnostic Progress</h3>
              <OSILadderViz
                layers={osiLadder.layers}
                currentLayer={osiLadder.currentLayer}
                showResults
              />
            </div>

            {/* Manual Tools */}
            <div className="flex-1 overflow-hidden">
              <ManualToolPanel
                tools={tools}
                onExecute={toolPanel.executeTool}
                results={toolPanel.results}
                executingTool={toolPanel.executingTool}
              />
            </div>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}
```

---

## URL State

```typescript
// Using nuqs for URL state management
import { useQueryState } from 'nuqs'

function ChatPageClient() {
  const [sessionId, setSessionId] = useQueryState('session')
  
  // Load session from URL on mount
  useEffect(() => {
    if (sessionId) {
      chat.loadConversation(sessionId)
    }
  }, [sessionId])
  
  // Update URL when session changes
  const handleSessionSelect = (id: string) => {
    setSessionId(id)
  }
}
```

---

## Loading States

```typescript
// app/chat/loading.tsx
import { Skeleton } from '@/components/ui/skeleton'

export default function ChatLoading() {
  return (
    <div className="flex h-[calc(100vh-56px)]">
      {/* Sidebar skeleton */}
      <div className="hidden md:block w-64 border-r p-4 space-y-4">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-8 w-full" />
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
      
      {/* Chat skeleton */}
      <div className="flex-1 p-4">
        <div className="flex flex-col items-center justify-center h-full">
          <Skeleton className="h-8 w-64 mb-4" />
          <Skeleton className="h-4 w-48" />
        </div>
      </div>
    </div>
  )
}
```

---

## Error Handling

```typescript
// app/chat/error.tsx
'use client'

export default function ChatError({
  error,
  reset
}: {
  error: Error
  reset: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center h-[calc(100vh-56px)]">
      <h2 className="text-xl font-semibold mb-4">Something went wrong</h2>
      <p className="text-muted-foreground mb-4">{error.message}</p>
      <button
        onClick={reset}
        className="px-4 py-2 bg-primary text-primary-foreground rounded"
      >
        Try again
      </button>
    </div>
  )
}
```

---

## Accessibility

| Feature | Implementation |
|---------|---------------|
| Landmarks | Main, aside, nav regions |
| Focus management | Focus trap in panels |
| Keyboard nav | Tab through all elements |
| Screen reader | Announce new messages |

---

## Test Specifications

### Page Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Page renders | All panels visible on desktop |
| Session loads from URL | Conversation displayed |
| New session clears state | Empty chat, reset OSI ladder |

### Integration Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Send message updates all panels | Message in chat, tool runs, OSI updates |
| Manual tool updates OSI | Layer state changes |
| Session switch loads history | Previous messages shown |

### Responsive Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Mobile shows chat only | Sidebar/right panel hidden |
| Tablet shows two columns | Sidebar as sheet |
| Desktop shows all three | Full layout |

---

## Lint/Build Verification

- [ ] Page renders without errors
- [ ] Server components fetch data
- [ ] Client components hydrate
- [ ] Responsive layout works
- [ ] URL state syncs
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All tests pass

---

## Related Documents

- [ChatWindow.md](../chat/ChatWindow.md) - Chat component
- [OSILadderViz.md](../diagnostics/OSILadderViz.md) - OSI visualization
- [ManualToolPanel.md](../diagnostics/ManualToolPanel.md) - Tool panel
- [Sidebar.md](../layout/Sidebar.md) - Session sidebar
- [use-chat.md](../../hooks/use-chat.md) - Chat hook

