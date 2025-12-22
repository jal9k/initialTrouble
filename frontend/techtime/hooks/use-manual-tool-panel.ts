// hooks/use-manual-tool-panel.ts

'use client'

import { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import { executeTool as apiExecuteTool } from '@/lib/api'
import type { DiagnosticTool, ToolResult } from '@/types'

// ============================================================================
// Hook Options
// ============================================================================

export interface UseManualToolPanelOptions {
  /** Available tools */
  tools: DiagnosticTool[]
  
  /** Callback on tool execution complete */
  onExecutionComplete?: (result: ToolResult) => void
  
  /** Callback on execution error */
  onExecutionError?: (error: Error) => void
}

// ============================================================================
// Hook Return Type
// ============================================================================

export interface UseManualToolPanelReturn {
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

// ============================================================================
// Hook Implementation
// ============================================================================

export function useManualToolPanel(
  options: UseManualToolPanelOptions
): UseManualToolPanelReturn {
  const { tools, onExecutionComplete, onExecutionError } = options

  const [expandedTool, setExpandedTool] = useState<string | null>(null)
  const [executingTool, setExecutingTool] = useState<string | null>(null)
  const [results, setResults] = useState<Map<string, ToolResult>>(new Map())

  // Store callbacks in refs to avoid stale closures
  const callbacksRef = useRef({ onExecutionComplete, onExecutionError })
  useEffect(() => {
    callbacksRef.current = { onExecutionComplete, onExecutionError }
  }, [onExecutionComplete, onExecutionError])

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
      callbacksRef.current.onExecutionComplete?.(result)
    } catch (error) {
      const toolResult: ToolResult = {
        toolCallId: '',
        name: toolName,
        result: null,
        error: error instanceof Error ? error.message : 'Unknown error'
      }
      setResults(prev => new Map(prev).set(toolName, toolResult))
      callbacksRef.current.onExecutionError?.(
        error instanceof Error ? error : new Error('Unknown error')
      )
    } finally {
      setExecutingTool(null)
    }
  }, [])

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

