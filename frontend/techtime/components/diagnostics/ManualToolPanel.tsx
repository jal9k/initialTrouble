'use client'

import { useState, useMemo, useCallback } from 'react'
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
import { Trash2, PlayCircle, Loader2 } from 'lucide-react'
import type { DiagnosticTool, ToolResult, ManualToolPanelProps } from '@/types'

const categoryLabels: Record<string, string> = {
  connectivity: 'Connectivity',
  dns: 'DNS',
  wifi: 'WiFi',
  ip_config: 'IP Configuration',
  system: 'System'
}

interface ExtendedManualToolPanelProps extends ManualToolPanelProps {
  /** Current tool execution results */
  results?: Map<string, ToolResult>
  
  /** Currently executing tool */
  executingTool?: string | null
  
  /** Callback to clear all results */
  onClearAll?: () => void
}

export function ManualToolPanel({
  tools,
  onExecute,
  results = new Map(),
  executingTool = null,
  onClearAll,
  className
}: ExtendedManualToolPanelProps) {
  // State for expanded tool
  const [expandedTool, setExpandedTool] = useState<string | null>(null)
  
  // State for running all tools
  const [isRunningAll, setIsRunningAll] = useState(false)

  // Get tools sorted by OSI layer for "Run All"
  const toolsInOSIOrder = useMemo(() => {
    // One tool per layer, sorted by osiLayer
    const layerToolMap = new Map<number, DiagnosticTool>()
    tools.forEach(tool => {
      // Only take first tool per layer (avoid duplicates)
      if (!layerToolMap.has(tool.osiLayer)) {
        layerToolMap.set(tool.osiLayer, tool)
      }
    })
    return Array.from(layerToolMap.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([, tool]) => tool)
  }, [tools])

  const handleRunAll = useCallback(async () => {
    setIsRunningAll(true)
    try {
      // Run tools sequentially in OSI order
      for (const tool of toolsInOSIOrder) {
        await onExecute(tool.name, {})
      }
    } finally {
      setIsRunningAll(false)
    }
  }, [toolsInOSIOrder, onExecute])

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

  const isExecuting = executingTool !== null || isRunningAll

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <h3 className="font-semibold text-sm">Manual Diagnostics</h3>
        <div className="flex items-center gap-1">
          {hasResults && onClearAll && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              onClick={onClearAll}
              disabled={isExecuting}
            >
              <Trash2 className="h-3 w-3 mr-1" />
              Clear
            </Button>
          )}
        </div>
      </div>
      
      {/* Run All Button */}
      <div className="p-3 border-b">
        <Button
          onClick={handleRunAll}
          disabled={isExecuting}
          className="w-full"
          variant="default"
        >
          {isRunningAll ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Running All Tests...
            </>
          ) : (
            <>
              <PlayCircle className="h-4 w-4 mr-2" />
              Run All Diagnostics
            </>
          )}
        </Button>
      </div>

      {/* Tool List */}
      <ScrollArea className="flex-1">
        <div className="pb-4">
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
                <AccordionContent className="px-2 pb-4 space-y-2">
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
        </div>
      </ScrollArea>
    </div>
  )
}

