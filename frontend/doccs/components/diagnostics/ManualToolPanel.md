# ManualToolPanel Component

This document specifies the ManualToolPanel component for manually executing diagnostic tools.

## File Location

```
frontend/
  components/
    diagnostics/
      ManualToolPanel.tsx
```

---

## Overview

The ManualToolPanel component provides:
- Accordion list of all diagnostic tools
- Tool execution interface
- Execution history
- Category filtering

This component uses a **headless pattern** for maximum reusability.

---

## Headless API

### Hook Interface

```typescript
interface UseManualToolPanelOptions {
  /** Available tools */
  tools: DiagnosticTool[]
  
  /** Callback on tool execution complete */
  onExecutionComplete?: (result: ToolResult) => void
  
  /** Callback on execution error */
  onExecutionError?: (error: Error) => void
}

interface UseManualToolPanelReturn {
  // State
  tools: DiagnosticTool[]
  expandedTool: string | null
  executingTool: string | null
  results: Map<string, ToolResult>
  
  // Derived State
  toolsByCategory: Map<string, DiagnosticTool[]>
  hasExecutingTool: boolean
  
  // Actions
  toggleTool: (toolName: string) => void
  executeTool: (toolName: string, params: Record<string, unknown>) => Promise<void>
  clearResult: (toolName: string) => void
  clearAllResults: () => void
}
```

### Hook Implementation

```typescript
'use client'

import { useState, useCallback, useMemo } from 'react'
import { executeTool as apiExecuteTool } from '@/lib/api'
import type { DiagnosticTool, ToolResult } from '@/types'

export function useManualToolPanel(
  options: UseManualToolPanelOptions
): UseManualToolPanelReturn {
  const { tools, onExecutionComplete, onExecutionError } = options

  const [expandedTool, setExpandedTool] = useState<string | null>(null)
  const [executingTool, setExecutingTool] = useState<string | null>(null)
  const [results, setResults] = useState<Map<string, ToolResult>>(new Map())

  const toggleTool = useCallback((toolName: string) => {
    setExpandedTool(prev => prev === toolName ? null : toolName)
  }, [])

  const executeTool = useCallback(async (
    toolName: string,
    params: Record<string, unknown>
  ) => {
    setExecutingTool(toolName)
    try {
      const result = await apiExecuteTool({ toolName, parameters: params })
      setResults(prev => new Map(prev).set(toolName, result))
      onExecutionComplete?.(result)
    } catch (error) {
      const toolResult: ToolResult = {
        toolCallId: '',
        name: toolName,
        result: null,
        error: error instanceof Error ? error.message : 'Unknown error'
      }
      setResults(prev => new Map(prev).set(toolName, toolResult))
      onExecutionError?.(error instanceof Error ? error : new Error('Unknown error'))
    } finally {
      setExecutingTool(null)
    }
  }, [onExecutionComplete, onExecutionError])

  const clearResult = useCallback((toolName: string) => {
    setResults(prev => {
      const next = new Map(prev)
      next.delete(toolName)
      return next
    })
  }, [])

  const clearAllResults = useCallback(() => {
    setResults(new Map())
  }, [])

  // Group tools by category
  const toolsByCategory = useMemo(() => {
    const grouped = new Map<string, DiagnosticTool[]>()
    tools.forEach(tool => {
      const category = tool.category
      if (!grouped.has(category)) {
        grouped.set(category, [])
      }
      grouped.get(category)!.push(tool)
    })
    return grouped
  }, [tools])

  const hasExecutingTool = executingTool !== null

  return {
    tools,
    expandedTool,
    executingTool,
    results,
    toolsByCategory,
    hasExecutingTool,
    toggleTool,
    executeTool,
    clearResult,
    clearAllResults
  }
}
```

---

## Props Interface

```typescript
interface ManualToolPanelProps {
  /** Available diagnostic tools */
  tools: DiagnosticTool[]
  
  /** Callback when tool is executed */
  onExecute: (toolName: string, params: Record<string, unknown>) => void
  
  /** Current tool execution results */
  results?: Map<string, ToolResult>
  
  /** Currently executing tool */
  executingTool?: string | null
  
  /** Additional CSS classes */
  className?: string
}
```

---

## Component Structure

```
┌─────────────────────────────────────────────────────────────┐
│  ManualToolPanel                                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Manual Diagnostics                    [Clear All]    │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Connectivity                                         │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  ToolCard: check_adapter_status               │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  ToolCard: ping_gateway                        │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  DNS                                                  │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  ToolCard: test_dns_resolution                 │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  ToolCard: ping_dns                            │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component States

| State | Description | Visual |
|-------|-------------|--------|
| Default | All tools collapsed | Compact list |
| Expanded | One tool open | Parameters visible |
| Executing | Tool running | Spinner on that tool |
| Has Results | Previous results | Results in cards |

---

## Behaviors

### Category Grouping
- Tools grouped by category
- Collapsible category sections
- Count badge per category

### Tool Execution
- Only one tool expanded at a time (optional)
- Execute sends to API
- Results cached per tool

### Clear Results
- Clear individual result
- Clear all results button
- Confirmation for clear all

---

## shadcn/ui Dependencies

| Component | Usage |
|-----------|-------|
| `Accordion` | Category sections |
| `ScrollArea` | Scrollable content |
| `Button` | Clear actions |
| `Separator` | Section dividers |

---

## Styling Guidelines

### Container
```css
.tool-panel {
  @apply flex flex-col h-full;
}

.tool-panel-header {
  @apply flex items-center justify-between p-3 border-b;
}

.tool-panel-content {
  @apply flex-1 overflow-hidden;
}
```

### Category Section
```css
.category-section {
  @apply border-b;
}

.category-header {
  @apply flex items-center justify-between p-3;
  @apply cursor-pointer hover:bg-muted/50;
  @apply font-medium text-sm;
}

.category-content {
  @apply p-2 space-y-2;
}
```

---

## Implementation

```typescript
'use client'

import { useMemo } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger
} from '@/components/ui/accordion'
import { ToolCard } from './ToolCard'
import { Trash2 } from 'lucide-react'
import type { DiagnosticTool, ToolResult } from '@/types'

const categoryLabels: Record<string, string> = {
  connectivity: 'Connectivity',
  dns: 'DNS',
  wifi: 'WiFi',
  ip_config: 'IP Configuration',
  system: 'System'
}

export function ManualToolPanel({
  tools,
  onExecute,
  results = new Map(),
  executingTool = null,
  className
}: ManualToolPanelProps) {
  // State for expanded tool
  const [expandedTool, setExpandedTool] = useState<string | null>(null)

  // Group tools by category
  const toolsByCategory = useMemo(() => {
    const grouped = new Map<string, DiagnosticTool[]>()
    tools.forEach(tool => {
      const category = tool.category
      if (!grouped.has(category)) {
        grouped.set(category, [])
      }
      grouped.get(category)!.push(tool)
    })
    return grouped
  }, [tools])

  const handleToggleTool = (toolName: string) => {
    setExpandedTool(prev => prev === toolName ? null : toolName)
  }

  const hasResults = results.size > 0

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <h3 className="font-semibold text-sm">Manual Diagnostics</h3>
        {hasResults && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={() => {/* clear all */}}
          >
            <Trash2 className="h-3 w-3 mr-1" />
            Clear All
          </Button>
        )}
      </div>

      {/* Tool List */}
      <ScrollArea className="flex-1">
        <Accordion type="single" collapsible className="w-full">
          {Array.from(toolsByCategory.entries()).map(([category, categoryTools]) => (
            <AccordionItem key={category} value={category}>
              <AccordionTrigger className="px-3 py-2 hover:bg-muted/50">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">
                    {categoryLabels[category] || category}
                  </span>
                  <Badge variant="secondary" className="text-xs">
                    {categoryTools.length}
                  </Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-2 pb-2 space-y-2">
                {categoryTools.map(tool => (
                  <ToolCard
                    key={tool.name}
                    tool={tool}
                    isExpanded={expandedTool === tool.name}
                    isExecuting={executingTool === tool.name}
                    onToggle={() => handleToggleTool(tool.name)}
                    onExecute={(params) => onExecute(tool.name, params)}
                    lastResult={results.get(tool.name)}
                  />
                ))}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </ScrollArea>
    </div>
  )
}
```

---

## Usage Example (Headless)

```typescript
'use client'

import { useManualToolPanel } from '@/hooks/use-manual-tool-panel'
import { ManualToolPanel } from '@/components/diagnostics/ManualToolPanel'

function DiagnosticsPage() {
  const {
    tools,
    expandedTool,
    executingTool,
    results,
    toggleTool,
    executeTool,
    clearAllResults
  } = useManualToolPanel({
    tools: availableTools,
    onExecutionComplete: (result) => {
      console.log('Tool completed:', result)
    }
  })

  return (
    <ManualToolPanel
      tools={tools}
      onExecute={executeTool}
      results={results}
      executingTool={executingTool}
    />
  )
}
```

---

## Accessibility

| Feature | Implementation |
|---------|---------------|
| Keyboard nav | Tab through tools, Enter to expand |
| ARIA | Proper accordion attributes |
| Focus | Focus management in accordion |
| Screen reader | Category and tool names announced |

---

## Test Specifications

### Render Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Categories rendered | All categories shown |
| Tools grouped | Tools in correct category |
| Category counts | Badge shows tool count |

### Interaction Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Category toggle | Expands/collapses |
| Tool toggle | Tool expands |
| Execute calls callback | onExecute invoked |
| Clear removes results | Results cleared |

### State Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Executing shows spinner | Correct tool shows loader |
| Results displayed | Last result in card |
| Only one expanded | Other tools collapse |

### Hook Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| `toggleTool` works | Expanded state changes |
| `executeTool` calls API | API request made |
| Results stored | Map updated with result |

---

## Lint/Build Verification

- [ ] Component properly typed
- [ ] Hook follows headless pattern
- [ ] Categories grouped correctly
- [ ] Accordion accessible
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All tests pass

---

## Related Documents

- [ToolCard.md](./ToolCard.md) - Individual tool cards
- [OSILadderViz.md](./OSILadderViz.md) - Layer visualization
- [chat-page.md](../pages/chat-page.md) - Page using this component
- [headless-patterns.md](../../headless-patterns.md) - Headless pattern guide
- [api.md](../../lib/api.md) - executeTool API function

