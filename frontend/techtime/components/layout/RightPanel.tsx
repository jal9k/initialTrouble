'use client'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from '@/components/ui/tooltip'
import {
  PanelRightClose,
  PanelRight,
  Layers,
  Wrench,
  Activity
} from 'lucide-react'
import { OSILadderViz } from '@/components/diagnostics/OSILadderViz'
import { ManualToolPanel } from '@/components/diagnostics/ManualToolPanel'
import type { LayerState, DiagnosticTool, ToolResult } from '@/types'

interface RightPanelProps {
  // OSI Ladder props
  layers: LayerState[]
  currentLayer?: number

  // Tool panel props
  tools: DiagnosticTool[]
  onExecute: (toolName: string, params: Record<string, unknown>) => void
  results?: Map<string, ToolResult>
  executingTool?: string | null
  onClearAll?: () => void

  // Panel state
  isCollapsed?: boolean
  onToggleCollapse?: () => void
  className?: string
}

export function RightPanel({
  layers,
  currentLayer,
  tools,
  onExecute,
  results = new Map(),
  executingTool = null,
  onClearAll,
  isCollapsed = false,
  onToggleCollapse,
  className
}: RightPanelProps) {
  const passedCount = layers.filter(l => l.status === 'pass').length
  const failedCount = layers.filter(l => l.status === 'fail').length
  const totalLayers = layers.length

  return (
    <aside
      className={cn(
        'border-l bg-gradient-to-b from-background to-muted/30 flex flex-col h-full transition-all duration-300 ease-in-out',
        isCollapsed ? 'w-16' : 'w-80',
        className
      )}
    >
      {/* Header */}
      <div className={cn(
        'border-b bg-background/50 backdrop-blur-sm shrink-0',
        isCollapsed ? 'p-2' : 'p-4'
      )}>
        <div className={cn(
          'flex items-center gap-2',
          isCollapsed ? 'flex-col' : 'justify-between'
        )}>
          {!isCollapsed && (
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" />
              <h2 className="font-semibold text-sm tracking-tight">Diagnostics</h2>
            </div>
          )}
          {onToggleCollapse && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onToggleCollapse}
                  className="h-8 w-8 shrink-0"
                >
                  {isCollapsed ? (
                    <PanelRight className="h-4 w-4" />
                  ) : (
                    <PanelRightClose className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="left">
                {isCollapsed ? 'Expand panel' : 'Collapse panel'}
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      </div>

      {isCollapsed ? (
        // Collapsed view - show icons only
        <div className="flex-1 flex flex-col items-center py-4 gap-4">
          <Tooltip>
            <TooltipTrigger asChild>
              <div className={cn(
                'p-2 rounded-lg cursor-pointer transition-colors',
                'hover:bg-muted',
                passedCount > 0 && 'bg-emerald-500/10',
                failedCount > 0 && 'bg-red-500/10'
              )}>
                <Layers className={cn(
                  'h-5 w-5',
                  passedCount === totalLayers && 'text-emerald-500',
                  failedCount > 0 && 'text-red-500',
                  passedCount === 0 && failedCount === 0 && 'text-muted-foreground'
                )} />
              </div>
            </TooltipTrigger>
            <TooltipContent side="left">
              <p className="font-medium">Diagnostic Progress</p>
              <p className="text-xs text-muted-foreground">
                {passedCount}/{totalLayers} layers passed
                {failedCount > 0 && `, ${failedCount} failed`}
              </p>
            </TooltipContent>
          </Tooltip>

          <div className="w-8 h-px bg-border" />

          <Tooltip>
            <TooltipTrigger asChild>
              <div className={cn(
                'p-2 rounded-lg cursor-pointer transition-colors',
                'hover:bg-muted',
                executingTool && 'bg-blue-500/10'
              )}>
                <Wrench className={cn(
                  'h-5 w-5',
                  executingTool ? 'text-blue-500 animate-pulse' : 'text-muted-foreground'
                )} />
              </div>
            </TooltipTrigger>
            <TooltipContent side="left">
              <p className="font-medium">Manual Tools</p>
              <p className="text-xs text-muted-foreground">
                {tools.length} tools available
                {executingTool && ` • Running: ${executingTool}`}
              </p>
            </TooltipContent>
          </Tooltip>

          {/* Quick status indicators */}
          <div className="flex-1" />
          
          <div className="flex flex-col gap-1">
            {layers.slice().reverse().map((layer) => (
              <Tooltip key={layer.layer.number}>
                <TooltipTrigger asChild>
                  <div
                    className={cn(
                      'w-3 h-3 rounded-full transition-colors',
                      layer.status === 'pass' && 'bg-emerald-500',
                      layer.status === 'fail' && 'bg-red-500',
                      layer.status === 'testing' && 'bg-blue-500 animate-pulse',
                      layer.status === 'pending' && 'bg-muted-foreground/30',
                      layer.status === 'skipped' && 'bg-muted-foreground/20'
                    )}
                  />
                </TooltipTrigger>
                <TooltipContent side="left">
                  <p className="text-xs">{layer.layer.name}: {layer.status}</p>
                </TooltipContent>
              </Tooltip>
            ))}
          </div>
        </div>
      ) : (
        // Expanded view
        <ScrollArea className="flex-1">
          {/* OSI Ladder Section */}
          <div className="p-4 border-b">
            <div className="flex items-center gap-2 mb-4">
              <div className="p-1.5 rounded-lg bg-primary/10">
                <Layers className="h-4 w-4 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-sm">Network Layers</h3>
                <p className="text-xs text-muted-foreground">
                  {passedCount}/{totalLayers} passed
                  {failedCount > 0 && (
                    <span className="text-red-500"> • {failedCount} failed</span>
                  )}
                </p>
              </div>
            </div>
            <OSILadderViz
              layers={layers}
              currentLayer={currentLayer}
              showResults
            />
          </div>

          {/* Manual Tools Section */}
          <div className="flex-1">
            <div className="flex items-center gap-2 p-4 pb-2">
              <div className="p-1.5 rounded-lg bg-primary/10">
                <Wrench className="h-4 w-4 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold text-sm">Manual Tools</h3>
                <p className="text-xs text-muted-foreground">
                  {tools.length} diagnostic tools
                </p>
              </div>
            </div>
            <ManualToolPanel
              tools={tools}
              onExecute={onExecute}
              results={results}
              executingTool={executingTool}
              onClearAll={onClearAll}
            />
          </div>
        </ScrollArea>
      )}

      {/* Footer - Status summary (expanded only) */}
      {!isCollapsed && (
        <div className="p-3 border-t bg-muted/30 shrink-0">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <div className={cn(
                'w-2 h-2 rounded-full',
                executingTool ? 'bg-blue-500 animate-pulse' : 'bg-muted-foreground/30'
              )} />
              {executingTool ? `Running ${executingTool}...` : 'Ready'}
            </span>
            <span>
              {results.size} result{results.size !== 1 ? 's' : ''} cached
            </span>
          </div>
        </div>
      )}
    </aside>
  )
}

