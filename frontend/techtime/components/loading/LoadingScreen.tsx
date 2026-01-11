'use client'

import { useState, useEffect } from 'react'
import { cn } from '@/lib/utils'

interface LoadingScreenProps {
  className?: string
  /** Called when the app is ready (from Python's onAppReady callback) */
  onReady?: () => void
  /** Called when an error occurs during initialization */
  onError?: (error: string) => void
}

interface LoadingState {
  status: string
  progress: number
  error: string | null
}

export function LoadingScreen({ className, onReady, onError }: LoadingScreenProps) {
  const [state, setState] = useState<LoadingState>({
    status: 'Initializing...',
    progress: 0,
    error: null
  })

  useEffect(() => {
    // Set up global callbacks for desktop mode
    if (typeof window !== 'undefined') {
      window.setLoadingStatus = (message: string) => {
        setState((prev) => ({ ...prev, status: message }))
      }

      window.setLoadingProgress = (percent: number, message: string) => {
        setState((prev) => ({
          ...prev,
          progress: percent,
          status: message || prev.status
        }))
      }

      // Chain with any existing callbacks and call the prop
      const existingOnAppReady = window.onAppReady
      window.onAppReady = () => {
        existingOnAppReady?.()
        onReady?.()
      }

      const existingOnAppError = window.onAppError
      window.onAppError = (error: string) => {
        existingOnAppError?.(error)
        setState((prev) => ({ ...prev, error }))
        onError?.(error)
      }
    }

    return () => {
      if (typeof window !== 'undefined') {
        window.setLoadingStatus = undefined
        window.setLoadingProgress = undefined
        window.onAppReady = undefined
        window.onAppError = undefined
      }
    }
  }, [onReady, onError])

  return (
    <div
      className={cn(
        'fixed inset-0 z-50 flex items-center justify-center',
        'bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900',
        className
      )}
    >
      <div className="w-full max-w-md px-8 text-center">
        {/* Logo/Title */}
        <h1 className="mb-8 text-4xl font-bold tracking-tight text-white">
          TechTim<span className="text-blue-400">(e)</span>
        </h1>

        {/* Error State */}
        {state.error && (
          <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 p-4">
            <p className="text-sm text-red-400">{state.error}</p>
          </div>
        )}

        {/* Loading State */}
        {!state.error && (
          <>
            {/* Progress Bar */}
            {state.progress > 0 && (
              <div className="mb-4 h-2 overflow-hidden rounded-full bg-slate-700">
                <div
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${state.progress}%` }}
                />
              </div>
            )}

            {/* Spinner (when no progress) */}
            {state.progress === 0 && (
              <div className="mb-4 flex justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-600 border-t-blue-500" />
              </div>
            )}

            {/* Status Message */}
            <p className="text-sm text-slate-400">{state.status}</p>
          </>
        )}
      </div>
    </div>
  )
}
