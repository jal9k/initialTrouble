# ToolCard Component

This document specifies the ToolCard component for displaying and executing individual diagnostic tools.

## File Location

```
frontend/
  components/
    diagnostics/
      ToolCard.tsx
```

---

## Overview

The ToolCard component displays:
- Tool name and description
- Parameter inputs
- Execute button
- Execution status
- Result display

---

## Props Interface

```typescript
interface ToolCardProps {
  /** Tool definition */
  tool: DiagnosticTool
  
  /** Whether the card is expanded */
  isExpanded: boolean
  
  /** Whether the tool is currently executing */
  isExecuting: boolean
  
  /** Callback to toggle expanded state */
  onToggle: () => void
  
  /** Callback to execute the tool */
  onExecute: (params: Record<string, unknown>) => void
  
  /** Last execution result */
  lastResult?: ToolResult
  
  /** Additional CSS classes */
  className?: string
}
```

---

## Component Structure

```
┌─────────────────────────────────────────────────────────────┐
│  ToolCard (Collapsed)                                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ⚡ ping_gateway                              [▼]     │  │
│  │  Ping the default gateway                             │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  ToolCard (Expanded)                                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ⚡ ping_gateway                              [▲]     │  │
│  │  Ping the default gateway                             │  │
│  │  ─────────────────────────────────────────────────── │  │
│  │  Parameters:                                          │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │  Timeout (ms): [1000        ]                   │ │  │
│  │  │  Count:        [4           ]                   │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  │                                                       │  │
│  │  [Execute]                                            │  │
│  │  ─────────────────────────────────────────────────── │  │
│  │  Last Result:                                         │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │  { "status": "success", "latency": 12 }         │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component States

| State | Description | Visual |
|-------|-------------|--------|
| Collapsed | Compact view | Name and description only |
| Expanded | Full view | Parameters and results |
| Executing | Running | Spinner, disabled inputs |
| Has Result | Completed | Result section visible |

---

## Behaviors

### Expand/Collapse
- Click header to toggle
- Animated transition
- Preserves parameter values

### Parameter Handling
- Renders appropriate input for each type
- Validates required parameters
- Shows defaults

### Execution
- Validate before execute
- Show loading state
- Display result or error

---

## shadcn/ui Dependencies

| Component | Usage |
|-----------|-------|
| `Card` | Container |
| `Collapsible` | Expand/collapse |
| `Input` | Parameter inputs |
| `Label` | Parameter labels |
| `Button` | Execute action |
| `Badge` | Category tag |

---

## Styling Guidelines

### Card Styling
```css
.tool-card {
  @apply border rounded-lg transition-colors;
}

.tool-card-header {
  @apply flex items-center justify-between p-3;
  @apply cursor-pointer hover:bg-muted/50;
}

.tool-card-content {
  @apply p-3 pt-0 space-y-4;
}
```

### Parameter Input
```css
.param-grid {
  @apply grid gap-3;
}

.param-field {
  @apply space-y-1;
}

.param-label {
  @apply text-sm font-medium;
}

.param-input {
  @apply w-full;
}
```

### Result Display
```css
.result-container {
  @apply bg-muted rounded-md p-3;
  @apply font-mono text-xs;
  @apply max-h-48 overflow-auto;
}
```

---

## Implementation

```typescript
'use client'

import { useState, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger
} from '@/components/ui/collapsible'
import { ChevronDown, Loader2, Play, Zap } from 'lucide-react'
import type { DiagnosticTool, ToolParameter, ToolResult } from '@/types'

function ParameterInput({
  param,
  value,
  onChange,
  disabled
}: {
  param: ToolParameter
  value: unknown
  onChange: (value: unknown) => void
  disabled: boolean
}) {
  switch (param.type) {
    case 'boolean':
      return (
        <Switch
          checked={Boolean(value)}
          onCheckedChange={onChange}
          disabled={disabled}
        />
      )
    case 'number':
      return (
        <Input
          type="number"
          value={value as number || ''}
          onChange={(e) => onChange(Number(e.target.value))}
          disabled={disabled}
          placeholder={String(param.default || '')}
        />
      )
    case 'string':
    default:
      return (
        <Input
          type="text"
          value={value as string || ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder={String(param.default || '')}
        />
      )
  }
}

export function ToolCard({
  tool,
  isExpanded,
  isExecuting,
  onToggle,
  onExecute,
  lastResult,
  className
}: ToolCardProps) {
  const [params, setParams] = useState<Record<string, unknown>>(() => {
    // Initialize with defaults
    const defaults: Record<string, unknown> = {}
    tool.parameters.forEach(p => {
      if (p.default !== undefined) {
        defaults[p.name] = p.default
      }
    })
    return defaults
  })

  const handleParamChange = useCallback((name: string, value: unknown) => {
    setParams(prev => ({ ...prev, [name]: value }))
  }, [])

  const handleExecute = () => {
    // Validate required params
    const missingRequired = tool.parameters
      .filter(p => p.required && params[p.name] === undefined)
      .map(p => p.name)

    if (missingRequired.length > 0) {
      // Could show validation error
      console.error('Missing required params:', missingRequired)
      return
    }

    onExecute(params)
  }

  const hasParameters = tool.parameters.length > 0

  return (
    <Card className={cn('overflow-hidden', className)}>
      <Collapsible open={isExpanded} onOpenChange={onToggle}>
        {/* Header */}
        <CollapsibleTrigger asChild>
          <div className="flex items-center justify-between p-3 cursor-pointer hover:bg-muted/50 transition-colors">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-muted-foreground" />
              <span className="font-mono text-sm font-medium">
                {tool.name}
              </span>
              <Badge variant="secondary" className="text-xs">
                {tool.category}
              </Badge>
            </div>
            <ChevronDown
              className={cn(
                'h-4 w-4 text-muted-foreground transition-transform',
                isExpanded && 'rotate-180'
              )}
            />
          </div>
        </CollapsibleTrigger>

        {/* Description (always visible) */}
        <div className="px-3 pb-3">
          <p className="text-sm text-muted-foreground">
            {tool.description}
          </p>
        </div>

        {/* Expanded content */}
        <CollapsibleContent>
          <div className="px-3 pb-3 space-y-4 border-t pt-3">
            {/* Parameters */}
            {hasParameters && (
              <div className="space-y-3">
                <h4 className="text-sm font-medium">Parameters</h4>
                <div className="grid gap-3">
                  {tool.parameters.map(param => (
                    <div key={param.name} className="space-y-1">
                      <Label className="text-xs flex items-center gap-1">
                        {param.name}
                        {param.required && (
                          <span className="text-destructive">*</span>
                        )}
                      </Label>
                      <ParameterInput
                        param={param}
                        value={params[param.name]}
                        onChange={(v) => handleParamChange(param.name, v)}
                        disabled={isExecuting}
                      />
                      <p className="text-xs text-muted-foreground">
                        {param.description}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Execute button */}
            <Button
              onClick={handleExecute}
              disabled={isExecuting}
              className="w-full"
            >
              {isExecuting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Executing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Execute
                </>
              )}
            </Button>

            {/* Last result */}
            {lastResult && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Last Result</h4>
                <div className="bg-muted rounded-md p-3 font-mono text-xs max-h-48 overflow-auto">
                  {lastResult.error ? (
                    <span className="text-destructive">{lastResult.error}</span>
                  ) : (
                    <pre>
                      {typeof lastResult.result === 'object'
                        ? JSON.stringify(lastResult.result, null, 2)
                        : String(lastResult.result)}
                    </pre>
                  )}
                </div>
                {lastResult.duration && (
                  <p className="text-xs text-muted-foreground">
                    Completed in {lastResult.duration}ms
                  </p>
                )}
              </div>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
```

---

## Accessibility

| Feature | Implementation |
|---------|---------------|
| Keyboard nav | Space/Enter toggles, Tab through inputs |
| Labels | All inputs have associated labels |
| Required | Required fields marked with asterisk |
| Focus | Focus management on expand |

---

## Test Specifications

### Render Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Tool name displayed | Name shown in header |
| Description displayed | Description visible |
| Category badge shown | Badge with category |
| Parameters rendered | Input for each param |

### State Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Collapsed hides content | Only header visible |
| Expanded shows all | Parameters and button visible |
| Executing shows spinner | Loader in button |
| Result displayed | Last result shown |

### Interaction Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Header click toggles | Expand/collapse |
| Param change updates state | Value stored |
| Execute calls callback | onExecute invoked with params |
| Disabled during execution | Inputs disabled |

### Validation Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Required params validated | Execute blocked if missing |
| Defaults populated | Default values shown |
| Type coercion works | Numbers parsed correctly |

---

## Lint/Build Verification

- [ ] Component properly typed
- [ ] All param types handled
- [ ] Validation works
- [ ] Loading state works
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All tests pass

---

## Related Documents

- [ManualToolPanel.md](./ManualToolPanel.md) - Parent panel component
- [OSILadderViz.md](./OSILadderViz.md) - Layer visualization
- [interfaces.md](../../types/interfaces.md) - DiagnosticTool type

