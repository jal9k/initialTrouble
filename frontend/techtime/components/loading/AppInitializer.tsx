'use client'

import { useState, useEffect, useCallback } from 'react'
import { LoadingScreen } from './LoadingScreen'
import { isDesktopMode, waitForPyWebView, unifiedApi } from '@/lib/pywebview-api'

interface AppInitializerProps {
  children: React.ReactNode
}

/**
 * AppInitializer handles application initialization for both desktop and HTTP modes.
 *
 * In desktop mode (PyWebView):
 * - Waits for the PyWebView API to become available
 * - Shows LoadingScreen until the Python backend signals ready
 * - LoadingScreen handles window.onAppReady and calls our onReady callback
 *
 * In HTTP mode:
 * - Checks if the backend is available
 * - Shows error if connection fails
 */
export function AppInitializer({ children }: AppInitializerProps) {
  const [isReady, setIsReady] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isDesktop, setIsDesktop] = useState(false)

  useEffect(() => {
    async function initialize() {
      // Check if we're in desktop mode by waiting briefly for PyWebView
      const isPyWebView = await waitForPyWebView(3000)
      setIsDesktop(isPyWebView)

      if (isPyWebView) {
        // Desktop mode: LoadingScreen will handle window.onAppReady
        // and call our handleReady callback when Python signals ready
        return
      }

      // HTTP mode: check API availability
      try {
        const ready = await unifiedApi.isReady()
        if (ready) {
          setIsReady(true)
        } else {
          // Backend not available, but don't show error - just proceed
          // The app will show connection errors when trying to use features
          setIsReady(true)
        }
      } catch {
        // In HTTP mode, we can proceed even if backend isn't available
        // Individual components will handle connection errors gracefully
        setIsReady(true)
      }
    }

    initialize()
  }, [])

  // Callbacks for LoadingScreen
  const handleReady = useCallback(() => {
    setIsReady(true)
  }, [])

  const handleError = useCallback((err: string) => {
    setError(err)
  }, [])

  // In HTTP mode, always show children (no loading screen needed)
  if (!isDesktop) {
    return <>{children}</>
  }

  // In desktop mode, show loading screen until ready
  if (!isReady && !error) {
    return <LoadingScreen onReady={handleReady} onError={handleError} />
  }

  // Show error state if initialization failed
  if (error) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <div className="max-w-md text-center px-8">
          <h1 className="mb-4 text-2xl font-bold text-white">Initialization Error</h1>
          <p className="mb-6 text-slate-400">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
