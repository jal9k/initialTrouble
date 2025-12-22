// hooks/use-tool-execution.ts

'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import type { ToolExecutionState, ToolExecutionStatus } from '@/types'

// ============================================================================
// Hook Options
// ============================================================================

export interface UseToolExecutionOptions {
  /** Initial tool state */
  initialState?: ToolExecutionState
  
  /** Callback on status change */
  onStatusChange?: (status: ToolExecutionStatus) => void
  
  /** Auto-collapse delay after success (ms) */
  autoCollapseDelay?: number
}

// ============================================================================
// Hook Return Type
// ============================================================================

export interface UseToolExecutionReturn {
  // State
  state: ToolExecutionState
  isExecuting: boolean
  isSuccess: boolean
  isError: boolean
  duration: number | null
  
  // Actions
  start: (toolName: string) => void
  complete: (result: unknown) => void
  fail: (error: string) => void
  reset: () => void
}

// ============================================================================
// Hook Implementation
// ============================================================================

const initialToolState: ToolExecutionState = {
  toolName: '',
  status: 'idle'
}

export function useToolExecution(
  options: UseToolExecutionOptions = {}
): UseToolExecutionReturn {
  const { initialState, onStatusChange } = options

  const [state, setState] = useState<ToolExecutionState>(
    initialState || initialToolState
  )

  const startTimeRef = useRef<Date | null>(null)
  const callbackRef = useRef(onStatusChange)

  // Update callback ref
  useEffect(() => {
    callbackRef.current = onStatusChange
  }, [onStatusChange])

  // Notify on status change
  useEffect(() => {
    callbackRef.current?.(state.status)
  }, [state.status])

  const start = useCallback((toolName: string) => {
    startTimeRef.current = new Date()
    setState({
      toolName,
      status: 'executing',
      startTime: startTimeRef.current
    })
  }, [])

  const complete = useCallback((result: unknown) => {
    const endTime = new Date()
    setState(prev => ({
      ...prev,
      status: 'success',
      endTime,
      result
    }))
  }, [])

  const fail = useCallback((error: string) => {
    const endTime = new Date()
    setState(prev => ({
      ...prev,
      status: 'error',
      endTime,
      error
    }))
  }, [])

  const reset = useCallback(() => {
    startTimeRef.current = null
    setState(initialToolState)
  }, [])

  const duration = state.startTime && state.endTime
    ? state.endTime.getTime() - state.startTime.getTime()
    : null

  return {
    state,
    isExecuting: state.status === 'executing',
    isSuccess: state.status === 'success',
    isError: state.status === 'error',
    duration,
    start,
    complete,
    fail,
    reset
  }
}

