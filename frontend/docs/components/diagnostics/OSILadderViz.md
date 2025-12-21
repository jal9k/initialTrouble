# OSILadderViz Component

This document specifies the OSILadderViz component for visualizing diagnostic progress through network layers.

## File Location

```
frontend/
  components/
    diagnostics/
      OSILadderViz.tsx
```

---

## Overview

The OSILadderViz component displays:
- 5 diagnostic layers (simplified OSI model)
- Current layer being tested
- Pass/fail/pending states per layer
- Real-time updates during diagnostics
- Interactive layer selection

This component uses a **headless pattern** for maximum reusability.

---

## Headless API

### Hook Interface

```typescript
interface UseOSILadderOptions {
  /** Initial layer states */
  initialLayers?: LayerState[]
  
  /** Callback when layer state changes */
  onLayerChange?: (layer: number, state: LayerStatus) => void
  
  /** Callback when all tests complete */
  onComplete?: (results: LayerState[]) => void
}

interface UseOSILadderReturn {
  // State
  layers: LayerState[]
  currentLayer: number | null
  isComplete: boolean
  
  // Derived State
  passedCount: number
  failedCount: number
  pendingCount: number
  overallStatus: 'pending' | 'passing' | 'failing' | 'complete'
  
  // Actions
  setLayerStatus: (layer: number, status: LayerStatus, result?: string) => void
  startLayer: (layer: number) => void
  passLayer: (layer: number, result?: string) => void
  failLayer: (layer: number, result?: string) => void
  reset: () => void
}
```

### Hook Implementation

```typescript
'use client'

import { useState, useCallback, useMemo } from 'react'
import type { LayerState, LayerStatus, OSILayer } from '@/types'
import { DIAGNOSTIC_LAYERS } from '@/types'

function createInitialLayers(): LayerState[] {
  return DIAGNOSTIC_LAYERS.map(layer => ({
    layer,
    status: 'pending' as LayerStatus
  }))
}

export function useOSILadder(
  options: UseOSILadderOptions = {}
): UseOSILadderReturn {
  const { initialLayers, onLayerChange, onComplete } = options

  const [layers, setLayers] = useState<LayerState[]>(
    initialLayers || createInitialLayers()
  )
  const [currentLayer, setCurrentLayer] = useState<number | null>(null)

  const setLayerStatus = useCallback((
    layerNum: number,
    status: LayerStatus,
    result?: string
  ) => {
    setLayers(prev => prev.map(l =>
      l.layer.number === layerNum
        ? { ...l, status, testResult: result, testedAt: new Date() }
        : l
    ))
    onLayerChange?.(layerNum, status)

    // Check if all complete
    setLayers(prev => {
      const allComplete = prev.every(l =>
        l.status === 'pass' || l.status === 'fail' || l.status === 'skipped'
      )
      if (allComplete) {
        onComplete?.(prev)
      }
      return prev
    })
  }, [onLayerChange, onComplete])

  const startLayer = useCallback((layerNum: number) => {
    setCurrentLayer(layerNum)
    setLayerStatus(layerNum, 'testing')
  }, [setLayerStatus])

  const passLayer = useCallback((layerNum: number, result?: string) => {
    setLayerStatus(layerNum, 'pass', result)
    setCurrentLayer(null)
  }, [setLayerStatus])

  const failLayer = useCallback((layerNum: number, result?: string) => {
    setLayerStatus(layerNum, 'fail', result)
    setCurrentLayer(null)
  }, [setLayerStatus])

  const reset = useCallback(() => {
    setLayers(createInitialLayers())
    setCurrentLayer(null)
  }, [])

  // Derived state
  const passedCount = useMemo(
    () => layers.filter(l => l.status === 'pass').length,
    [layers]
  )
  const failedCount = useMemo(
    () => layers.filter(l => l.status === 'fail').length,
    [layers]
  )
  const pendingCount = useMemo(
    () => layers.filter(l => l.status === 'pending').length,
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

## Props Interface

```typescript
interface OSILadderVizProps {
  /** Layer states to display */
  layers: LayerState[]
  
  /** Currently active layer (0-indexed) */
  currentLayer?: number
  
  /** Callback when layer is clicked */
  onLayerClick?: (layer: number) => void
  
  /** Show detailed results */
  showResults?: boolean
  
  /** Additional CSS classes */
  className?: string
}
```

---

## Component Structure

```
┌─────────────────────────────────────────┐
│  OSILadderViz                           │
│  ┌───────────────────────────────────┐  │
│  │ 5 │ ○ Internet           pending  │  │
│  │───│───────────────────────────────│  │
│  │ 4 │ ○ DNS                pending  │  │
│  │───│───────────────────────────────│  │
│  │ 3 │ ◉ Gateway           testing  │◄─── Current
│  │───│───────────────────────────────│  │
│  │ 2 │ ✓ IP Config            pass  │  │
│  │───│───────────────────────────────│  │
│  │ 1 │ ✓ Physical/Link        pass  │  │
│  └───────────────────────────────────┘  │
│                                         │
│  Progress: 2/5 ████████░░░░░░░░        │
└─────────────────────────────────────────┘
```

---

## Component States

| State | Description | Visual |
|-------|-------------|--------|
| Pending | Not yet tested | Gray circle, muted text |
| Testing | Currently running | Pulsing blue circle, active styling |
| Pass | Test passed | Green checkmark |
| Fail | Test failed | Red X |
| Skipped | Test skipped | Gray dash |

---

## Behaviors

### Visual Progression
- Layers displayed from bottom (Physical) to top (Internet)
- Current layer highlighted with animation
- Completed layers show checkmark or X
- Progress bar shows overall completion

### Interactive Mode
- Layers clickable when onLayerClick provided
- Hover effects on clickable layers
- Tooltips show layer descriptions

### Real-time Updates
- Smooth transitions between states
- Pulse animation for testing state
- Entry animation for new states

---

## shadcn/ui Dependencies

| Component | Usage |
|-----------|-------|
| `Progress` | Overall progress bar |
| `Tooltip` | Layer descriptions |
| `Badge` | Status indicators |

---

## Styling Guidelines

### Layer Status Colors
```css
.layer-pending {
  @apply text-muted-foreground;
}

.layer-testing {
  @apply text-blue-500 dark:text-blue-400;
  @apply animate-pulse;
}

.layer-pass {
  @apply text-green-500 dark:text-green-400;
}

.layer-fail {
  @apply text-red-500 dark:text-red-400;
}

.layer-skipped {
  @apply text-muted-foreground opacity-50;
}
```

### Status Icons
```css
.status-icon {
  @apply h-5 w-5 flex items-center justify-center rounded-full;
}

.icon-pending {
  @apply border-2 border-muted-foreground;
}

.icon-testing {
  @apply border-2 border-blue-500 bg-blue-500/20;
}

.icon-pass {
  @apply bg-green-500 text-white;
}

.icon-fail {
  @apply bg-red-500 text-white;
}
```

### Layout
```css
.ladder-container {
  @apply flex flex-col-reverse gap-1;
}

.layer-row {
  @apply flex items-center gap-3 p-2 rounded-lg;
  @apply transition-colors;
}

.layer-row-active {
  @apply bg-blue-500/10;
}

.layer-row-clickable {
  @apply cursor-pointer hover:bg-muted;
}
```

---

## Implementation

```typescript
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

const statusConfig: Record<LayerStatus, {
  icon: typeof Check
  className: string
  iconClass: string
}> = {
  pending: {
    icon: Circle,
    className: 'text-muted-foreground',
    iconClass: 'border-2 border-current'
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

export function OSILadderViz({
  layers,
  currentLayer,
  onLayerClick,
  showResults = false,
  className
}: OSILadderVizProps) {
  const passedCount = layers.filter(l => l.status === 'pass').length
  const progress = (passedCount / layers.length) * 100
  const isInteractive = !!onLayerClick

  // Reverse layers for bottom-up display
  const displayLayers = [...layers].reverse()

  return (
    <div className={cn('space-y-4', className)}>
      {/* Ladder */}
      <div className="flex flex-col gap-1">
        {displayLayers.map((layerState, index) => {
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
                  <span className={cn(
                    'flex-1 font-medium',
                    isActive && 'text-blue-500'
                  )}>
                    {layerState.layer.name}
                  </span>

                  {/* Status text */}
                  <span className="text-xs">
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
          <span>{passedCount}/{layers.length}</span>
        </div>
        <Progress value={progress} className="h-2" />
      </div>
    </div>
  )
}
```

---

## Usage Example (Headless)

```typescript
'use client'

import { useOSILadder } from '@/hooks/use-osi-ladder'
import { OSILadderViz } from '@/components/diagnostics/OSILadderViz'

function DiagnosticProgress() {
  const {
    layers,
    currentLayer,
    startLayer,
    passLayer,
    failLayer,
    overallStatus
  } = useOSILadder({
    onComplete: (results) => {
      console.log('All tests complete:', results)
    }
  })

  // Simulate diagnostic flow
  useEffect(() => {
    const runDiagnostics = async () => {
      for (let i = 1; i <= 5; i++) {
        startLayer(i)
        await sleep(1000)
        // Simulate pass/fail
        if (Math.random() > 0.2) {
          passLayer(i, 'OK')
        } else {
          failLayer(i, 'Connection failed')
          break // Stop on failure
        }
      }
    }
    runDiagnostics()
  }, [])

  return (
    <div>
      <OSILadderViz
        layers={layers}
        currentLayer={currentLayer}
        showResults
      />
      <p>Status: {overallStatus}</p>
    </div>
  )
}
```

---

## Accessibility

| Feature | Implementation |
|---------|---------------|
| Keyboard nav | Tab through layers, Enter/Space to select |
| Screen reader | Layer states announced |
| Focus visible | Focus rings on interactive layers |
| Color contrast | Status colors meet WCAG AA |

---

## Test Specifications

### Render Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| All layers rendered | 5 layers displayed |
| Correct order | Bottom-up (1 at bottom) |
| Progress bar shown | Bar with percentage |

### State Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Pending shows circle | Empty circle icon |
| Testing shows spinner | Rotating loader |
| Pass shows checkmark | Green check icon |
| Fail shows X | Red X icon |
| Current layer highlighted | Blue background |

### Interaction Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Layer click calls callback | onLayerClick invoked |
| Keyboard Enter triggers | Same as click |
| Tooltip shows on hover | Description visible |

### Hook Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| `startLayer` sets testing | Status becomes 'testing' |
| `passLayer` sets pass | Status becomes 'pass' |
| `failLayer` sets fail | Status becomes 'fail' |
| `reset` clears all | All return to pending |
| Counts calculated | passedCount, failedCount accurate |

---

## Lint/Build Verification

- [ ] Component properly typed
- [ ] Hook follows headless pattern
- [ ] All layer states handled
- [ ] Animations performant
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All tests pass

---

## Related Documents

- [ManualToolPanel.md](./ManualToolPanel.md) - Tool execution panel
- [ToolCard.md](./ToolCard.md) - Individual tool cards
- [chat-page.md](../pages/chat-page.md) - Page using this component
- [headless-patterns.md](../../headless-patterns.md) - Headless pattern guide
- [interfaces.md](../../types/interfaces.md) - LayerState types

