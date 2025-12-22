'use client'

import { cn } from '@/lib/utils'
import { Progress } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from '@/components/ui/tooltip'
import { Check, X, Minus, Circle, Loader2 } from 'lucide-react'
import type { LayerStatus, OSILadderVizProps } from '@/types'

const statusConfig: Record<LayerStatus, {
  icon: typeof Check
  className: string
  iconClass: string
}> = {
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
                      e.preventDefault()
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
                    'flex-1 font-medium text-sm',
                    isActive && 'text-blue-500'
                  )}>
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
          <span>{passedCount}/{layers.length}</span>
        </div>
        <Progress value={progress} className="h-2" />
      </div>
    </div>
  )
}

