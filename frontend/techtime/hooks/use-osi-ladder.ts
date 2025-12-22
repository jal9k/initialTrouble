// hooks/use-osi-ladder.ts

'use client'

import { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import type { LayerState, LayerStatus } from '@/types'
import { DIAGNOSTIC_LAYERS } from '@/types'

// ============================================================================
// Hook Options
// ============================================================================

export interface UseOSILadderOptions {
  /** Initial layer states */
  initialLayers?: LayerState[]
  
  /** Callback when layer state changes */
  onLayerChange?: (layer: number, state: LayerStatus) => void
  
  /** Callback when all tests complete */
  onComplete?: (results: LayerState[]) => void
}

// ============================================================================
// Hook Return Type
// ============================================================================

export interface UseOSILadderReturn {
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

// ============================================================================
// Helper Functions
// ============================================================================

function createInitialLayers(): LayerState[] {
  return DIAGNOSTIC_LAYERS.map(layer => ({
    layer,
    status: 'pending' as LayerStatus
  }))
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useOSILadder(
  options: UseOSILadderOptions = {}
): UseOSILadderReturn {
  const { initialLayers, onLayerChange, onComplete } = options

  const [layers, setLayers] = useState<LayerState[]>(
    initialLayers || createInitialLayers()
  )
  const [currentLayer, setCurrentLayer] = useState<number | null>(null)

  // Store callbacks in refs to avoid stale closures
  const callbacksRef = useRef({ onLayerChange, onComplete })
  useEffect(() => {
    callbacksRef.current = { onLayerChange, onComplete }
  }, [onLayerChange, onComplete])

  const setLayerStatus = useCallback((
    layerNum: number,
    status: LayerStatus,
    result?: string
  ) => {
    setLayers(prev => {
      const updated = prev.map(l =>
        l.layer.number === layerNum
          ? { ...l, status, testResult: result, testedAt: new Date() }
          : l
      )
      
      // Notify layer change
      callbacksRef.current.onLayerChange?.(layerNum, status)
      
      // Check if all complete
      const allComplete = updated.every(l =>
        l.status === 'pass' || l.status === 'fail' || l.status === 'skipped'
      )
      if (allComplete) {
        callbacksRef.current.onComplete?.(updated)
      }
      
      return updated
    })
  }, [])

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

