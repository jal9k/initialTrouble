# Phase 4.3: Diagnostics Components

Implementing OSILadderViz, ToolCard, and ManualToolPanel.

---

## Prerequisites

- Phase 4.2 completed
- Types from Phase 1 (DIAGNOSTIC_LAYERS, LayerState, etc.)

---

## Step 1: Create useOSILadder Hook

Create `hooks/use-osi-ladder.ts`:

```typescript
// hooks/use-osi-ladder.ts
'use client'

import { useState, useCallback, useMemo } from 'react'
import type { LayerState, LayerStatus, OSILayer } from '@/types'
import { DIAGNOSTIC_LAYERS } from '@/types'

function createInitialLayers(): LayerState[] {
  return DIAGNOSTIC_LAYERS.map((layer) => ({
    layer,
    status: 'pending' as LayerStatus
  }))
}

interface UseOSILadderOptions {
  initialLayers?: LayerState[]
  onLayerChange?: (layer: number, status: LayerStatus) => void
  onComplete?: (results: LayerState[]) => void
}

interface UseOSILadderReturn {
  layers: LayerState[]
  currentLayer: number | null
  isComplete: boolean
  passedCount: number
  failedCount: number
  pendingCount: number
  overallStatus: 'pending' | 'passing' | 'failing' | 'complete'
  setLayerStatus: (layer: number, status: LayerStatus, result?: string) => void
  startLayer: (layer: number) => void
  passLayer: (layer: number, result?: string) => void
  failLayer: (layer: number, result?: string) => void
  reset: () => void
}

export function useOSILadder(
  options: UseOSILadderOptions = {}
): UseOSILadderReturn {
  const { initialLayers, onLayerChange, onComplete } = options

  const [layers, setLayers] = useState<LayerState[]>(
    initialLayers || createInitialLayers()
  )
  const [currentLayer, setCurrentLayer] = useState<number | null>(null)

  const setLayerStatus = useCallback(
    (layerNum: number, status: LayerStatus, result?: string) => {
      setLayers((prev) => {
        const updated = prev.map((l) =>
          l.layer.number === layerNum
            ? { ...l, status, testResult: result, testedAt: new Date() }
            : l
        )

        // Check if all complete
        const allComplete = updated.every(
          (l) =>
            l.status === 'pass' || l.status === 'fail' || l.status === 'skipped'
        )
        if (allComplete) {
          onComplete?.(updated)
        }

        return updated
      })
      onLayerChange?.(layerNum, status)
    },
    [onLayerChange, onComplete]
  )

  const startLayer = useCallback(
    (layerNum: number) => {
      setCurrentLayer(layerNum)
      setLayerStatus(layerNum, 'testing')
    },
    [setLayerStatus]
  )

  const passLayer = useCallback(
    (layerNum: number, result?: string) => {
      setLayerStatus(layerNum, 'pass', result)
      setCurrentLayer(null)
    },
    [setLayerStatus]
  )

  const failLayer = useCallback(
    (layerNum: number, result?: string) => {
      setLayerStatus(layerNum, 'fail', result)
      setCurrentLayer(null)
    },
    [setLayerStatus]
  )

  const reset = useCallback(() => {
    setLayers(createInitialLayers())
    setCurrentLayer(null)
  }, [])

  // Derived state
  const passedCount = useMemo(
    () => layers.filter((l) => l.status === 'pass').length,
    [layers]
  )
  const failedCount = useMemo(
    () => layers.filter((l) => l.status === 'fail').length,
    [layers]
  )
  const pendingCount = useMemo(
    () => layers.filter((l) => l.status === 'pending').length,
    [layers]
  )
  const isComplete = pendingCount === 0 && currentLayer === null

  const overallStatus = useMemo(() => {
    if (isComplete) return 'complete'
    if (failedCount > 0) return 'failing'
    if (passedCount > 0) return 'passing'
    return 'pending'
  }, [isComplete, failedCount, passedCount])

  return {
    layers,
    currentLayer,
    isComplete,
    passedCount,
    failedCount,
    pendingCount,
    overallStatus,
    setLayerStatus,
    startLayer,
    passLayer,
    failLayer,
    reset
  }
}
```

---

## Step 2: Create OSILadderViz Component

Create `components/diagnostics/OSILadderViz.tsx`:

```typescript
// components/diagnostics/OSILadderViz.tsx
'use client'

import { cn } from '@/lib/utils'
import { Progress } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from '@/components/ui/tooltip'
import { Check, X, Minus, Circle, Loader2 } from 'lucide-react'
import type { LayerState, LayerStatus } from '@/types'

const statusConfig: Record<
  LayerStatus,
  { icon: typeof Check; className: string; iconClass: string }
> = {
  pending: {
    icon: Circle,
    className: 'text-muted-foreground',
    iconClass: 'border-2 border-current rounded-full'
  },
  testing: {
    icon: Loader2,
    className: 'text-blue-500',
    iconClass: 'animate-spin'
  },
  pass: {
    icon: Check,
    className: 'text-green-500',
    iconClass: 'bg-green-500 text-white rounded-full p-0.5'
  },
  fail: {
    icon: X,
    className: 'text-red-500',
    iconClass: 'bg-red-500 text-white rounded-full p-0.5'
  },
  skipped: {
    icon: Minus,
    className: 'text-muted-foreground opacity-50',
    iconClass: ''
  }
}

interface OSILadderVizProps {
  layers: LayerState[]
  currentLayer?: number | null
  onLayerClick?: (layer: number) => void
  showResults?: boolean
  className?: string
}

export function OSILadderViz({
  layers,
  currentLayer,
  onLayerClick,
  showResults = false,
  className
}: OSILadderVizProps) {
  const passedCount = layers.filter((l) => l.status === 'pass').length
  const progress = (passedCount / layers.length) * 100
  const isInteractive = !!onLayerClick

  // Reverse layers for bottom-up display
  const displayLayers = [...layers].reverse()

  return (
    <div className={cn('space-y-4', className)}>
      {/* Ladder */}
      <div className="flex flex-col gap-1">
        {displayLayers.map((layerState) => {
          const config = statusConfig[layerState.status]
          const Icon = config.icon
          const isActive = layerState.layer.number === currentLayer
          const layerNum = layerState.layer.number

          return (
            <Tooltip key={layerNum}>
              <TooltipTrigger asChild>
                <div
                  onClick={() => isInteractive && onLayerClick?.(layerNum)}
                  className={cn(
                    'flex items-center gap-3 p-2 rounded-lg transition-colors',
                    isActive && 'bg-blue-500/10',
                    isInteractive && 'cursor-pointer hover:bg-muted',
                    config.className
                  )}
                  role={isInteractive ? 'button' : undefined}
                  tabIndex={isInteractive ? 0 : undefined}
                  onKeyDown={(e) => {
                    if (isInteractive && (e.key === 'Enter' || e.key === ' ')) {
                      onLayerClick?.(layerNum)
                    }
                  }}
                >
                  {/* Layer number */}
                  <span className="w-6 text-center text-sm font-mono text-muted-foreground">
                    {layerNum}
                  </span>

                  {/* Status icon */}
                  <div className="w-6 h-6 flex items-center justify-center">
                    <Icon className={cn('h-4 w-4', config.iconClass)} />
                  </div>

                  {/* Layer name */}
                  <span
                    className={cn(
                      'flex-1 font-medium text-sm',
                      isActive && 'text-blue-500'
                    )}
                  >
                    {layerState.layer.name}
                  </span>

                  {/* Status text */}
                  <span className="text-xs capitalize">
                    {layerState.status}
                  </span>
                </div>
              </TooltipTrigger>
              <TooltipContent side="right">
                <div className="space-y-1">
                  <p className="font-medium">{layerState.layer.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {layerState.layer.description}
                  </p>
                  {layerState.testResult && showResults && (
                    <p className="text-xs mt-2 font-mono">
                      {layerState.testResult}
                    </p>
                  )}
                </div>
              </TooltipContent>
            </Tooltip>
          )
        })}
      </div>

      {/* Progress bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Progress</span>
          <span>
            {passedCount}/{layers.length}
          </span>
        </div>
        <Progress value={progress} className="h-2" />
      </div>
    </div>
  )
}
```

---

## Step 3: Create ToolCard Component

Create `components/diagnostics/ToolCard.tsx`:

```typescript
// components/diagnostics/ToolCard.tsx
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
          value={(value as number) ?? ''}
          onChange={(e) => onChange(Number(e.target.value))}
          disabled={disabled}
          placeholder={String(param.default ?? '')}
        />
      )
    case 'string':
    default:
      return (
        <Input
          type="text"
          value={(value as string) ?? ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder={String(param.default ?? '')}
        />
      )
  }
}

interface ToolCardProps {
  tool: DiagnosticTool
  isExpanded: boolean
  isExecuting: boolean
  onToggle: () => void
  onExecute: (params: Record<string, unknown>) => void
  lastResult?: ToolResult
  className?: string
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
    const defaults: Record<string, unknown> = {}
    tool.parameters.forEach((p) => {
      if (p.default !== undefined) {
        defaults[p.name] = p.default
      }
    })
    return defaults
  })

  const handleParamChange = useCallback((name: string, value: unknown) => {
    setParams((prev) => ({ ...prev, [name]: value }))
  }, [])

  const handleExecute = () => {
    const missingRequired = tool.parameters
      .filter((p) => p.required && params[p.name] === undefined)
      .map((p) => p.name)

    if (missingRequired.length > 0) {
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
              <span className="font-mono text-sm font-medium">{tool.name}</span>
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

        {/* Description */}
        <div className="px-3 pb-3">
          <p className="text-sm text-muted-foreground">{tool.description}</p>
        </div>

        {/* Expanded content */}
        <CollapsibleContent>
          <div className="px-3 pb-3 space-y-4 border-t pt-3">
            {/* Parameters */}
            {hasParameters && (
              <div className="space-y-3">
                <h4 className="text-sm font-medium">Parameters</h4>
                <div className="grid gap-3">
                  {tool.parameters.map((param) => (
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

## Step 4: Create useManualToolPanel Hook

Create `hooks/use-manual-tool-panel.ts`:

```typescript
// hooks/use-manual-tool-panel.ts
'use client'

import { useState, useCallback, useMemo } from 'react'
import { executeTool } from '@/lib/api'
import type { DiagnosticTool, ToolResult } from '@/types'

interface UseManualToolPanelOptions {
  tools: DiagnosticTool[]
  onExecutionComplete?: (result: ToolResult) => void
  onExecutionError?: (error: Error) => void
}

interface UseManualToolPanelReturn {
  tools: DiagnosticTool[]
  expandedTool: string | null
  executingTool: string | null
  results: Map<string, ToolResult>
  toolsByCategory: Map<string, DiagnosticTool[]>
  hasExecutingTool: boolean
  toggleTool: (toolName: string) => void
  executeTool: (
    toolName: string,
    params: Record<string, unknown>
  ) => Promise<void>
  clearResult: (toolName: string) => void
  clearAllResults: () => void
}

export function useManualToolPanel(
  options: UseManualToolPanelOptions
): UseManualToolPanelReturn {
  const { tools, onExecutionComplete, onExecutionError } = options

  const [expandedTool, setExpandedTool] = useState<string | null>(null)
  const [executingTool, setExecutingTool] = useState<string | null>(null)
  const [results, setResults] = useState<Map<string, ToolResult>>(new Map())

  const toggleTool = useCallback((toolName: string) => {
    setExpandedTool((prev) => (prev === toolName ? null : toolName))
  }, [])

  const executeToolAction = useCallback(
    async (toolName: string, params: Record<string, unknown>) => {
      setExecutingTool(toolName)
      try {
        const result = await executeTool({ toolName, parameters: params })
        setResults((prev) => new Map(prev).set(toolName, result))
        onExecutionComplete?.(result)
      } catch (error) {
        const toolResult: ToolResult = {
          toolCallId: '',
          name: toolName,
          result: null,
          error: error instanceof Error ? error.message : 'Unknown error'
        }
        setResults((prev) => new Map(prev).set(toolName, toolResult))
        onExecutionError?.(
          error instanceof Error ? error : new Error('Unknown error')
        )
      } finally {
        setExecutingTool(null)
      }
    },
    [onExecutionComplete, onExecutionError]
  )

  const clearResult = useCallback((toolName: string) => {
    setResults((prev) => {
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
    tools.forEach((tool) => {
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
    executeTool: executeToolAction,
    clearResult,
    clearAllResults
  }
}
```

---

## Step 5: Create ManualToolPanel Component

Create `components/diagnostics/ManualToolPanel.tsx`:

```typescript
// components/diagnostics/ManualToolPanel.tsx
'use client'

import { useState, useMemo } from 'react'
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

interface ManualToolPanelProps {
  tools: DiagnosticTool[]
  onExecute: (toolName: string, params: Record<string, unknown>) => void
  results?: Map<string, ToolResult>
  executingTool?: string | null
  onClearAll?: () => void
  className?: string
}

export function ManualToolPanel({
  tools,
  onExecute,
  results = new Map(),
  executingTool = null,
  onClearAll,
  className
}: ManualToolPanelProps) {
  const [expandedTool, setExpandedTool] = useState<string | null>(null)

  // Group tools by category
  const toolsByCategory = useMemo(() => {
    const grouped = new Map<string, DiagnosticTool[]>()
    tools.forEach((tool) => {
      const category = tool.category
      if (!grouped.has(category)) {
        grouped.set(category, [])
      }
      grouped.get(category)!.push(tool)
    })
    return grouped
  }, [tools])

  const handleToggleTool = (toolName: string) => {
    setExpandedTool((prev) => (prev === toolName ? null : toolName))
  }

  const hasResults = results.size > 0

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <h3 className="font-semibold text-sm">Manual Diagnostics</h3>
        {hasResults && onClearAll && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={onClearAll}
          >
            <Trash2 className="h-3 w-3 mr-1" />
            Clear All
          </Button>
        )}
      </div>

      {/* Tool List */}
      <ScrollArea className="flex-1">
        <Accordion type="single" collapsible className="w-full">
          {Array.from(toolsByCategory.entries()).map(
            ([category, categoryTools]) => (
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
                  {categoryTools.map((tool) => (
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
            )
          )}
        </Accordion>
      </ScrollArea>
    </div>
  )
}
```

---

## Step 6: Create Diagnostics Index Export

Create `components/diagnostics/index.ts`:

```typescript
// components/diagnostics/index.ts

export { OSILadderViz } from './OSILadderViz'
export { ToolCard } from './ToolCard'
export { ManualToolPanel } from './ManualToolPanel'
```

---

## Step 7: Update Hooks Index

Update `hooks/index.ts`:

```typescript
// hooks/index.ts

export { useWebSocket } from './use-websocket'
export type { UseWebSocketOptions, UseWebSocketReturn } from './use-websocket'

export { useChat } from './use-chat'
export type { UseChatOptions, UseChatReturn } from './use-chat'

export { useToolExecution } from './use-tool-execution'

export { useOSILadder } from './use-osi-ladder'

export { useManualToolPanel } from './use-manual-tool-panel'
```

---

## Step 8: Verify Phase 4.3

```bash
npx tsc --noEmit && npm run lint && npm run build
```

---

## Phase 4.3 Checklist

- [ ] useOSILadder hook created
- [ ] OSILadderViz displays all 5 layers
- [ ] OSILadderViz shows correct status icons
- [ ] OSILadderViz progress bar works
- [ ] OSILadderViz tooltips show descriptions
- [ ] ToolCard with parameter inputs
- [ ] ToolCard validation for required params
- [ ] ToolCard shows execution state
- [ ] ToolCard displays last result
- [ ] useManualToolPanel hook created
- [ ] ManualToolPanel groups by category
- [ ] ManualToolPanel clear all works
- [ ] `tsc --noEmit` passes
- [ ] `npm run lint` passes
- [ ] `npm run build` passes

**Gate: All checks must pass before proceeding to Phase 4.4**


