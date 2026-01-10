# Phase 3: Frontend Modifications (UPDATED)

## CHANGES FROM ORIGINAL

This document has been updated to match the actual TechTim(e) frontend codebase patterns.

| Task | Original Approach | Updated Approach | Reason |
|------|-------------------|------------------|--------|
| 3.2 API Client | `/api/chat`, `/api/sessions` | `/chat`, `/api/sessions` | Match actual FastAPI endpoints |
| 3.2 API Client | Minimal HTTP fallback | Full HTTP fallback with all endpoints | Support running without PyWebView |
| 3.3 Unified API Client | Create new file | Update existing `lib/api.ts` | Preserve existing API structure |
| 3.4 Chat Hook | Create new hook | Update existing `use-chat.ts` | Preserve `currentToolExecution`, callbacks |
| 3.5 Message Format | Generic messages | Match existing `Message` type with diagnostics | Keep `ResponseDiagnostics`, `VerificationResult` |

---

## Objective

Modify the Next.js frontend to communicate with the Python backend through PyWebView's JavaScript bridge when running as a desktop app, while maintaining compatibility with HTTP mode for development.

## Prerequisites

Before starting this phase, ensure you have:
- Phases 1-2 completed
- Frontend already scaffolded at `frontend/techtime/`
- Node.js 18+ installed
- Familiarity with the existing `use-chat.ts` and `lib/api.ts` patterns

---

## Task 3.1: Update Next.js Configuration for Static Export

### Purpose

PyWebView loads static HTML files directly. We need to configure Next.js to output a static export instead of requiring a server.

### File: `frontend/techtime/next.config.ts`

Update the Next.js configuration:

```typescript
import type { NextConfig } from 'next'

const config: NextConfig = {
  // Enable static export for PyWebView
  output: 'export',
  
  // Disable image optimization (requires server)
  images: {
    unoptimized: true,
  },
  
  // Generate trailing slashes for static file compatibility
  trailingSlash: true,
  
  // Base path is root (files are served from index.html)
  basePath: '',
  
  // Asset prefix for static loading
  assetPrefix: process.env.NODE_ENV === 'production' ? '' : undefined,
  
  // Disable server-only features
  typescript: {
    // Type checking in CI, not build
    ignoreBuildErrors: false,
  },
  
  eslint: {
    // Linting in CI, not build
    ignoreDuringBuilds: false,
  },
}

export default config
```

### Verification Steps

1. Build the frontend:
   ```bash
   cd frontend/techtime
   npm run build
   ```

2. Check that `out/` directory is created with `index.html`

3. Test static serving:
   ```bash
   npx serve out
   ```

---

## Task 3.2: Create PyWebView Type Definitions

### Purpose

TypeScript needs to know about the `window.pywebview` API that becomes available when running in PyWebView.

### File: `frontend/techtime/types/pywebview.d.ts` (NEW FILE)

```typescript
/**
 * Type definitions for PyWebView JavaScript bridge.
 *
 * When running in PyWebView, the Python API is exposed as window.pywebview.api.
 * These types match the TechTimApi class in desktop/api.py.
 */

interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  error?: string
}

interface ModelProgress {
  status: string
  completed: number
  total: number
  digest?: string
}

interface StreamChunk {
  type: 'content' | 'tool_call' | 'tool_result' | 'done' | 'error'
  data: Record<string, unknown>
}

interface ChatResponse {
  response: string
  tool_calls?: Array<{
    name: string
    arguments: Record<string, unknown>
    result?: string
    success?: boolean
    duration_ms?: number
  }> | null
  conversation_id: string | null
  diagnostics?: {
    confidence_score: number
    thoughts: string[]
    tools_used: Array<{
      name: string
      success: boolean
      duration_ms?: number
    }>
  } | null
}

interface SessionListResponse {
  id: string
  startTime: string
  outcome: string
  issueCategory?: string | null
  preview: string
  message_count: number
}

interface MessageResponse {
  id: string
  role: string
  content: string
  timestamp: string
}

interface ToolDefinition {
  name: string
  description: string
  parameters: Array<{
    name: string
    type: string
    description: string
    required: boolean
  }>
}

interface ToolExecutionResult {
  success: boolean
  content: string
}

interface ModelInfo {
  name: string
  size: number
  modified_at: string
  digest?: string
}

interface AppInfo {
  version: string
  bundled_mode: boolean
  ollama_host: string
  configured_model: string
  user_data_path: string
  ollama_running: boolean
}

interface AnalyticsSummaryResponse {
  total_sessions: number
  resolved_count: number
  unresolved_count: number
  abandoned_count: number
  in_progress_count: number
  avg_messages_per_session: number
  total_cost_usd: number
}

interface ToolStatsResponse {
  tool_name: string
  total_calls: number
  success_count: number
  failure_count: number
  avg_execution_time_ms: number
}

/**
 * PyWebView API Bridge
 *
 * All methods return Promises that resolve to ApiResponse objects.
 */
interface PyWebViewApi {
  // Session Management
  create_session(): Promise<ApiResponse<{ session_id: string }>>
  list_sessions(): Promise<ApiResponse<SessionListResponse[]>>
  get_session_messages(session_id: string): Promise<ApiResponse<MessageResponse[]>>
  delete_session(session_id: string): Promise<ApiResponse<void>>

  // Chat Operations
  send_message(
    session_id: string,
    message: string
  ): Promise<ApiResponse<ChatResponse>>
  send_message_streaming(
    session_id: string,
    message: string
  ): Promise<ApiResponse<{ status: string }>>

  // Tool Operations
  list_tools(): Promise<ApiResponse<ToolDefinition[]>>
  execute_tool(
    name: string,
    arguments: Record<string, unknown>
  ): Promise<ApiResponse<ToolExecutionResult>>

  // Model Management
  list_models(): Promise<ApiResponse<ModelInfo[]>>
  check_model_status(): Promise<ApiResponse<{ model: string; available: boolean }>>
  download_model(model_name: string): Promise<ApiResponse<{ status: string; model: string }>>

  // System Information
  get_app_info(): Promise<ApiResponse<AppInfo>>
  get_diagnostics(): Promise<ApiResponse<Record<string, unknown>>>

  // Analytics
  get_analytics_summary(): Promise<ApiResponse<AnalyticsSummaryResponse>>
  get_tool_stats(): Promise<ApiResponse<ToolStatsResponse[]>>
}

/**
 * PyWebView global object
 */
interface PyWebView {
  api: PyWebViewApi
}

/**
 * Global callback functions called by Python
 */
interface Window {
  pywebview?: PyWebView

  // Streaming callbacks
  onStreamChunk?: (chunk: StreamChunk) => void
  onStreamDone?: () => void
  onStreamError?: (error: string) => void

  // Model download callbacks
  onModelProgress?: (progress: ModelProgress) => void
  onModelDownloadComplete?: (modelName: string) => void
  onModelDownloadError?: (error: string) => void

  // Loading/initialization callbacks
  setLoadingStatus?: (message: string) => void
  setLoadingProgress?: (percent: number, message: string) => void
  onAppReady?: () => void
  onAppError?: (error: string) => void
}
```

---

## Task 3.3: Create Unified API Client

### Purpose

Create a unified API client that automatically uses PyWebView when available and falls back to HTTP otherwise. This allows the same code to work in both desktop and web modes.

### File: `frontend/techtime/lib/pywebview-api.ts` (NEW FILE)

```typescript
/**
 * PyWebView-aware API client for TechTim(e).
 *
 * This module provides a unified interface that:
 * - Uses PyWebView bridge when running in desktop mode
 * - Falls back to HTTP requests when running in browser
 *
 * Usage:
 *   import { api, isDesktopMode } from '@/lib/pywebview-api'
 *
 *   if (await api.isReady()) {
 *     const response = await api.sendMessage('session-123', 'Hello')
 *   }
 */

import type {
  SessionListItem,
  Message,
  SessionSummary,
  ToolStats,
  DiagnosticTool,
  ToolResult,
  SessionOutcome
} from '@/types'

// Re-use existing HTTP client as fallback
import * as httpApi from './api'

// ============================================================================
// Environment Detection
// ============================================================================

/**
 * Check if running inside PyWebView.
 */
export function isDesktopMode(): boolean {
  return typeof window !== 'undefined' && window.pywebview?.api !== undefined
}

/**
 * Wait for PyWebView API to become available.
 * In desktop mode, there's a brief moment after page load before the API is ready.
 */
export async function waitForPyWebView(
  timeoutMs: number = 5000
): Promise<boolean> {
  if (typeof window === 'undefined') return false

  const startTime = Date.now()

  while (Date.now() - startTime < timeoutMs) {
    if (window.pywebview?.api) {
      return true
    }
    await new Promise((resolve) => setTimeout(resolve, 100))
  }

  return false
}

// ============================================================================
// Unified API Client
// ============================================================================

/**
 * Helper to call PyWebView API and handle errors.
 */
async function pywebviewCall<T>(
  method: () => Promise<{ success: boolean; data?: T; error?: string }>
): Promise<T> {
  const response = await method()
  if (!response.success) {
    throw new Error(response.error || 'Unknown error')
  }
  return response.data as T
}

/**
 * Unified API that works in both desktop and web modes.
 */
export const unifiedApi = {
  // =========================================================================
  // Connection Status
  // =========================================================================

  /**
   * Check if the API is ready to use.
   */
  async isReady(): Promise<boolean> {
    if (isDesktopMode()) {
      try {
        const result = await window.pywebview!.api.get_app_info()
        return result.success
      } catch {
        return false
      }
    }

    // HTTP mode: check health endpoint
    try {
      await httpApi.getHealth()
      return true
    } catch {
      return false
    }
  },

  // =========================================================================
  // Session Management
  // =========================================================================

  /**
   * Create a new chat session.
   */
  async createSession(): Promise<string> {
    if (isDesktopMode()) {
      const result = await pywebviewCall(() =>
        window.pywebview!.api.create_session()
      )
      return result.session_id
    }

    // HTTP mode: sessions are created implicitly on first message
    // Return a client-generated ID that will be sent with the first message
    return `client-${Date.now()}-${Math.random().toString(36).slice(2)}`
  },

  /**
   * List all sessions.
   */
  async listSessions(): Promise<SessionListItem[]> {
    if (isDesktopMode()) {
      const sessions = await pywebviewCall(() =>
        window.pywebview!.api.list_sessions()
      )
      return sessions.map((s) => ({
        id: s.id,
        startTime: new Date(s.startTime),
        outcome: s.outcome as SessionOutcome,
        issueCategory: s.issueCategory as SessionListItem['issueCategory'],
        preview: s.preview
      }))
    }

    // HTTP mode
    const response = await httpApi.listSessions()
    return response.items
  },

  /**
   * Get messages for a session.
   */
  async getSessionMessages(sessionId: string): Promise<Message[]> {
    if (isDesktopMode()) {
      const messages = await pywebviewCall(() =>
        window.pywebview!.api.get_session_messages(sessionId)
      )
      return messages.map((m) => ({
        id: m.id,
        role: m.role as 'user' | 'assistant',
        content: m.content,
        timestamp: new Date(m.timestamp)
      }))
    }

    // HTTP mode
    return httpApi.getSessionMessages(sessionId)
  },

  /**
   * Delete a session.
   */
  async deleteSession(sessionId: string): Promise<boolean> {
    if (isDesktopMode()) {
      await pywebviewCall(() =>
        window.pywebview!.api.delete_session(sessionId)
      )
      return true
    }

    // HTTP mode
    const result = await httpApi.deleteSession(sessionId)
    return result.success
  },

  // =========================================================================
  // Chat Operations
  // =========================================================================

  /**
   * Send a message and get the response.
   * This is the non-streaming version.
   */
  async sendMessage(
    sessionId: string,
    message: string
  ): Promise<{
    content: string
    sessionId: string
    toolCalls?: Array<{
      name: string
      arguments: Record<string, unknown>
      result?: string
      success?: boolean
    }>
    diagnostics?: {
      confidenceScore: number
      thoughts: string[]
      toolsUsed: Array<{ name: string; success: boolean; durationMs?: number }>
    }
  }> {
    if (isDesktopMode()) {
      const response = await pywebviewCall(() =>
        window.pywebview!.api.send_message(sessionId, message)
      )

      return {
        content: response.response,
        sessionId: response.conversation_id || sessionId,
        toolCalls: response.tool_calls?.map((tc) => ({
          name: tc.name,
          arguments: tc.arguments,
          result: tc.result,
          success: tc.success
        })),
        diagnostics: response.diagnostics
          ? {
              confidenceScore: response.diagnostics.confidence_score,
              thoughts: response.diagnostics.thoughts,
              toolsUsed: response.diagnostics.tools_used.map((t) => ({
                name: t.name,
                success: t.success,
                durationMs: t.duration_ms
              }))
            }
          : undefined
      }
    }

    // HTTP mode: Use WebSocket via the existing hook
    // This function is mainly for PyWebView mode; HTTP mode uses WebSocket
    throw new Error(
      'Direct HTTP chat is not supported. Use the useChat hook for WebSocket communication.'
    )
  },

  /**
   * Send a message with streaming response.
   * Returns immediately; updates come via callbacks.
   */
  async sendMessageStreaming(
    sessionId: string,
    message: string,
    callbacks: {
      onContent?: (text: string) => void
      onToolCall?: (tool: { name: string; arguments: Record<string, unknown> }) => void
      onToolResult?: (result: { tool: string; success: boolean; content: string }) => void
      onDone?: (finalContent: string) => void
      onError?: (error: string) => void
    }
  ): Promise<void> {
    if (!isDesktopMode()) {
      throw new Error(
        'Streaming is only supported in desktop mode. Use WebSocket for HTTP mode.'
      )
    }

    // Set up callbacks
    window.onStreamChunk = (chunk) => {
      switch (chunk.type) {
        case 'content':
          callbacks.onContent?.(chunk.data.text as string)
          break
        case 'tool_call':
          callbacks.onToolCall?.({
            name: chunk.data.name as string,
            arguments: chunk.data.arguments as Record<string, unknown>
          })
          break
        case 'tool_result':
          callbacks.onToolResult?.({
            tool: chunk.data.tool as string,
            success: chunk.data.success as boolean,
            content: chunk.data.content as string
          })
          break
        case 'done':
          callbacks.onDone?.(chunk.data.final as string)
          break
        case 'error':
          callbacks.onError?.(chunk.data.message as string)
          break
      }
    }

    window.onStreamDone = () => {
      // Cleanup callbacks
      window.onStreamChunk = undefined
      window.onStreamDone = undefined
      window.onStreamError = undefined
    }

    window.onStreamError = (error) => {
      callbacks.onError?.(error)
      window.onStreamChunk = undefined
      window.onStreamDone = undefined
      window.onStreamError = undefined
    }

    // Start streaming
    await pywebviewCall(() =>
      window.pywebview!.api.send_message_streaming(sessionId, message)
    )
  },

  // =========================================================================
  // Tool Operations
  // =========================================================================

  /**
   * List available diagnostic tools.
   */
  async listTools(): Promise<DiagnosticTool[]> {
    if (isDesktopMode()) {
      const tools = await pywebviewCall(() =>
        window.pywebview!.api.list_tools()
      )
      return tools.map((t) => ({
        name: t.name,
        description: t.description,
        parameters: t.parameters.map((p) => ({
          name: p.name,
          type: p.type,
          description: p.description,
          required: p.required
        }))
      }))
    }

    // HTTP mode
    return httpApi.listTools()
  },

  /**
   * Execute a diagnostic tool manually.
   */
  async executeTool(
    name: string,
    args: Record<string, unknown>
  ): Promise<ToolResult> {
    if (isDesktopMode()) {
      const result = await pywebviewCall(() =>
        window.pywebview!.api.execute_tool(name, args)
      )
      return {
        toolCallId: `manual-${Date.now()}`,
        name,
        result: result.content,
        success: result.success
      }
    }

    // HTTP mode
    return httpApi.executeTool({ toolName: name, parameters: args })
  },

  // =========================================================================
  // Model Management (Desktop only)
  // =========================================================================

  /**
   * List downloaded Ollama models.
   */
  async listModels(): Promise<Array<{ name: string; size: number }>> {
    if (!isDesktopMode()) {
      throw new Error('Model management is only available in desktop mode')
    }

    return pywebviewCall(() => window.pywebview!.api.list_models())
  },

  /**
   * Check if the configured model is available.
   */
  async checkModelStatus(): Promise<{ model: string; available: boolean }> {
    if (!isDesktopMode()) {
      // In HTTP mode, assume model is available (Ollama manages it)
      return { model: 'unknown', available: true }
    }

    return pywebviewCall(() => window.pywebview!.api.check_model_status())
  },

  /**
   * Download a model.
   * Progress updates come via window.onModelProgress callback.
   */
  async downloadModel(
    modelName: string,
    callbacks: {
      onProgress?: (progress: { status: string; completed: number; total: number }) => void
      onComplete?: () => void
      onError?: (error: string) => void
    }
  ): Promise<void> {
    if (!isDesktopMode()) {
      throw new Error('Model download is only available in desktop mode')
    }

    // Set up callbacks
    window.onModelProgress = (progress) => {
      callbacks.onProgress?.(progress)
    }

    window.onModelDownloadComplete = () => {
      callbacks.onComplete?.()
      window.onModelProgress = undefined
      window.onModelDownloadComplete = undefined
      window.onModelDownloadError = undefined
    }

    window.onModelDownloadError = (error) => {
      callbacks.onError?.(error)
      window.onModelProgress = undefined
      window.onModelDownloadComplete = undefined
      window.onModelDownloadError = undefined
    }

    await pywebviewCall(() => window.pywebview!.api.download_model(modelName))
  },

  // =========================================================================
  // Analytics
  // =========================================================================

  /**
   * Get session analytics summary.
   */
  async getAnalyticsSummary(): Promise<SessionSummary> {
    if (isDesktopMode()) {
      const summary = await pywebviewCall(() =>
        window.pywebview!.api.get_analytics_summary()
      )
      return {
        totalSessions: summary.total_sessions,
        resolvedCount: summary.resolved_count,
        unresolvedCount: summary.unresolved_count,
        abandonedCount: summary.abandoned_count,
        inProgressCount: summary.in_progress_count,
        averageMessagesPerSession: summary.avg_messages_per_session,
        totalCostUsd: summary.total_cost_usd
      }
    }

    // HTTP mode
    return httpApi.getAnalyticsSummary()
  },

  /**
   * Get tool usage statistics.
   */
  async getToolStats(): Promise<ToolStats[]> {
    if (isDesktopMode()) {
      const stats = await pywebviewCall(() =>
        window.pywebview!.api.get_tool_stats()
      )
      return stats.map((s) => ({
        toolName: s.tool_name,
        totalCalls: s.total_calls,
        successCount: s.success_count,
        failureCount: s.failure_count,
        avgExecutionTimeMs: s.avg_execution_time_ms
      }))
    }

    // HTTP mode
    return httpApi.getToolStats()
  },

  // =========================================================================
  // App Info
  // =========================================================================

  /**
   * Get application information.
   */
  async getAppInfo(): Promise<{
    version: string
    desktopMode: boolean
    ollamaRunning: boolean
    configuredModel: string
  }> {
    if (isDesktopMode()) {
      const info = await pywebviewCall(() =>
        window.pywebview!.api.get_app_info()
      )
      return {
        version: info.version,
        desktopMode: info.bundled_mode,
        ollamaRunning: info.ollama_running,
        configuredModel: info.configured_model
      }
    }

    // HTTP mode
    const health = await httpApi.getHealth()
    return {
      version: '1.0.0',
      desktopMode: false,
      ollamaRunning: health.ollama?.available || false,
      configuredModel: health.ollama?.model || 'unknown'
    }
  }
}

// Export convenience alias
export { unifiedApi as api }
```

---

## Task 3.4: Create Loading Screen Component

### Purpose

Show a loading screen during app initialization (model download, Ollama startup, etc.).

### File: `frontend/techtime/components/loading/LoadingScreen.tsx` (NEW FILE)

```tsx
'use client'

import { useState, useEffect } from 'react'
import { cn } from '@/lib/utils'

interface LoadingScreenProps {
  className?: string
}

interface LoadingState {
  status: string
  progress: number
  error: string | null
  ready: boolean
}

export function LoadingScreen({ className }: LoadingScreenProps) {
  const [state, setState] = useState<LoadingState>({
    status: 'Initializing...',
    progress: 0,
    error: null,
    ready: false
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

      window.onAppReady = () => {
        setState((prev) => ({ ...prev, ready: true }))
      }

      window.onAppError = (error: string) => {
        setState((prev) => ({ ...prev, error }))
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
  }, [])

  // If ready, don't show loading screen
  if (state.ready) {
    return null
  }

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
```

---

## Task 3.5: Update useChat Hook for PyWebView Support

### Purpose

Modify the existing `use-chat.ts` hook to support both WebSocket (HTTP mode) and direct API calls (PyWebView mode).

### File: `frontend/techtime/hooks/use-chat.ts`

**IMPORTANT:** This is an UPDATE to the existing hook. Preserve:
- `currentToolExecution` tracking
- All callback patterns (`onToolStart`, `onToolComplete`, etc.)
- `ResponseDiagnostics` and `VerificationResult` handling
- Local storage persistence

Add the following changes:

```typescript
// hooks/use-chat.ts

'use client'

import { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import { useWebSocket } from './use-websocket'
import { getSessionMessages } from '@/lib/api'
import { isDesktopMode, unifiedApi } from '@/lib/pywebview-api'  // ADD THIS
import { generateId } from '@/lib/utils'
import type {
  Message,
  ToolCall,
  ToolResult,
  ServerMessage,
  SessionOutcome,
  ResponseDiagnostics,
  VerificationResult
} from '@/types'

// ... keep existing interfaces (UseChatOptions, UseChatReturn, etc.) ...

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const {
    initialConversationId,
    onSessionStart,
    onSessionEnd,
    onMessage,
    onToolStart,
    onToolComplete,
    persist = true
  } = options

  // State
  const [messages, setMessages] = useState<Message[]>([])
  const [conversationId, setConversationId] = useState<string | null>(
    initialConversationId || null
  )
  const [isStreaming, setIsStreaming] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [currentToolExecution, setCurrentToolExecution] = useState<ToolCall | null>(null)

  // NEW: Track if we're in desktop mode
  const [isDesktop, setIsDesktop] = useState(false)

  // Refs
  const pendingMessageRef = useRef<string | null>(null)
  const callbacksRef = useRef({
    onSessionStart,
    onSessionEnd,
    onMessage,
    onToolStart,
    onToolComplete
  })

  // Check desktop mode on mount
  useEffect(() => {
    setIsDesktop(isDesktopMode())
  }, [])

  // Update callbacks ref
  useEffect(() => {
    callbacksRef.current = {
      onSessionStart,
      onSessionEnd,
      onMessage,
      onToolStart,
      onToolComplete
    }
  }, [onSessionStart, onSessionEnd, onMessage, onToolStart, onToolComplete])

  // Handle incoming WebSocket messages (HTTP mode)
  const handleWebSocketMessage = useCallback(
    (serverMessage: ServerMessage) => {
      // ... keep existing implementation ...
    },
    [conversationId]
  )

  // WebSocket connection (HTTP mode only)
  const { send } = useWebSocket({
    onMessage: handleWebSocketMessage,
    // NEW: Disable WebSocket in desktop mode
    enabled: !isDesktop
  })

  // ... keep existing useEffect hooks for localStorage, etc. ...

  // UPDATED: sendMessage to support both modes
  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return

      setError(null)
      setIsStreaming(true)

      // Add user message
      const userMessage: Message = {
        id: generateId('msg'),
        role: 'user',
        content: content.trim(),
        timestamp: new Date()
      }

      setMessages((prev) => [...prev, userMessage])
      pendingMessageRef.current = content.trim()

      // NEW: Use different paths for desktop vs HTTP
      if (isDesktop) {
        // Desktop mode: use direct API call
        try {
          const sessionId = conversationId || (await unifiedApi.createSession())
          
          if (!conversationId) {
            setConversationId(sessionId)
            callbacksRef.current.onSessionStart?.(sessionId)
          }

          await unifiedApi.sendMessageStreaming(sessionId, content.trim(), {
            onToolCall: (tool) => {
              const toolCall: ToolCall = {
                id: generateId('tc'),
                name: tool.name,
                arguments: tool.arguments
              }
              setCurrentToolExecution(toolCall)
              callbacksRef.current.onToolStart?.(toolCall)
            },
            onToolResult: (result) => {
              const toolResult: ToolResult = {
                toolCallId: currentToolExecution?.id || '',
                name: result.tool,
                result: result.content,
                success: result.success
              }
              callbacksRef.current.onToolComplete?.(toolResult)
            },
            onDone: (finalContent) => {
              setIsStreaming(false)
              setCurrentToolExecution(null)

              const assistantMessage: Message = {
                id: generateId('msg'),
                role: 'assistant',
                content: finalContent,
                timestamp: new Date()
              }
              setMessages((prev) => [...prev, assistantMessage])
              callbacksRef.current.onMessage?.(assistantMessage)
            },
            onError: (errorMsg) => {
              setIsStreaming(false)
              setError(new Error(errorMsg))
            }
          })
        } catch (err) {
          setIsStreaming(false)
          setError(err instanceof Error ? err : new Error('Failed to send message'))
        }
      } else {
        // HTTP mode: use WebSocket (existing behavior)
        send({
          message: content.trim(),
          conversation_id: conversationId || undefined
        })
      }
    },
    [conversationId, send, isDesktop, currentToolExecution]
  )

  // UPDATED: loadConversation to support both modes
  const loadConversation = useCallback(async (id: string) => {
    setIsLoading(true)
    setError(null)

    try {
      let loadedMessages: Message[]

      if (isDesktop) {
        // Desktop mode: use unified API
        loadedMessages = await unifiedApi.getSessionMessages(id)
      } else {
        // HTTP mode: use existing API
        loadedMessages = await getSessionMessages(id)
      }

      // Convert date strings to Date objects
      const messagesWithDates = loadedMessages.map((m) => ({
        ...m,
        timestamp: new Date(m.timestamp)
      }))
      setMessages(messagesWithDates)
      setConversationId(id)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load conversation'))
    } finally {
      setIsLoading(false)
    }
  }, [isDesktop])

  // ... keep rest of existing implementation (clearMessages, startNewConversation, etc.) ...

  return {
    // State
    messages,
    conversationId,
    isStreaming,
    isLoading,
    error,
    currentToolExecution,

    // Derived
    isEmpty,
    lastMessage,
    lastUserMessage,
    lastAssistantMessage,
    messageCount,
    toolsUsed,

    // Actions
    sendMessage,
    clearMessages,
    loadConversation,
    startNewConversation,
    endConversation,
    retryLastMessage
  }
}
```

---

## Task 3.6: Update useWebSocket Hook

### Purpose

Add an `enabled` option to disable WebSocket in desktop mode.

### File: `frontend/techtime/hooks/use-websocket.ts`

Add to the options interface:

```typescript
export interface UseWebSocketOptions {
  url?: string
  onMessage?: (data: ServerMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Error) => void
  reconnectAttempts?: number
  reconnectInterval?: number
  enabled?: boolean  // ADD THIS
}
```

In the hook implementation, add early return if disabled:

```typescript
export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    url = WS_URL,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
    enabled = true  // ADD THIS
  } = options

  // ... existing state ...

  useEffect(() => {
    // ADD: Skip connection if disabled
    if (!enabled) {
      return
    }

    // ... rest of existing implementation ...
  }, [enabled, /* ... other deps ... */])

  // ... rest of implementation ...
}
```

---

## Task 3.7: Update Main Page

### Purpose

Add the loading screen and handle initialization.

### File: `frontend/techtime/app/page.tsx`

Update to include the loading screen:

```tsx
'use client'

import { useEffect, useState } from 'react'
import { LoadingScreen } from '@/components/loading/LoadingScreen'
import { isDesktopMode, waitForPyWebView, unifiedApi } from '@/lib/pywebview-api'
import { ChatWindow } from '@/components/chat/ChatWindow'
// ... other imports ...

export default function HomePage() {
  const [isReady, setIsReady] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function initialize() {
      // In desktop mode, wait for PyWebView
      if (typeof window !== 'undefined') {
        const isPyWebView = await waitForPyWebView(3000)

        if (isPyWebView) {
          // Desktop mode: Python handles initialization
          // The loading screen waits for onAppReady callback
          return
        }
      }

      // HTTP mode: check API availability
      try {
        const ready = await unifiedApi.isReady()
        if (ready) {
          setIsReady(true)
        } else {
          setError('Backend is not available. Please start the server.')
        }
      } catch (err) {
        setError('Failed to connect to backend.')
      }
    }

    initialize()
  }, [])

  // Listen for app ready (desktop mode)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      window.onAppReady = () => {
        setIsReady(true)
      }
      window.onAppError = (err: string) => {
        setError(err)
      }
    }

    return () => {
      if (typeof window !== 'undefined') {
        window.onAppReady = undefined
        window.onAppError = undefined
      }
    }
  }, [])

  // Show loading screen in desktop mode until ready
  if (isDesktopMode() && !isReady) {
    return <LoadingScreen />
  }

  // Show error if initialization failed
  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-900">
        <div className="max-w-md text-center">
          <h1 className="mb-4 text-2xl font-bold text-white">Connection Error</h1>
          <p className="text-slate-400">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  // Normal page content
  return (
    <main className="min-h-screen bg-slate-900">
      <ChatWindow />
    </main>
  )
}
```

---

## Task 3.8: Update Package Scripts

### Purpose

Add scripts for building and testing static export.

### File: `frontend/techtime/package.json`

Ensure these scripts exist:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "serve:static": "npx serve out -l 3000"
  }
}
```

---

## Acceptance Criteria

Phase 3 is complete when:

1. **Static export works**: Running `npm run build` creates `out/` with `index.html`

2. **PyWebView types are defined**: TypeScript recognizes `window.pywebview` without errors

3. **Unified API works**: `unifiedApi.isReady()` returns `true` in both modes

4. **Chat works in both modes**:
   - HTTP mode (Next.js dev server): WebSocket communication works
   - Desktop mode (PyWebView): Direct API calls work

5. **Loading screen shows**: In desktop mode, loading screen appears and shows progress

6. **Existing features preserved**: All existing chat functionality (tool tracking, diagnostics, persistence) continues to work

---

## Files Modified/Created Summary

| File | Action | Description |
|------|--------|-------------|
| `next.config.ts` | Modified | Added static export configuration |
| `types/pywebview.d.ts` | Created | TypeScript definitions for PyWebView |
| `lib/pywebview-api.ts` | Created | Unified API client for both modes |
| `components/loading/LoadingScreen.tsx` | Created | Loading screen component |
| `hooks/use-chat.ts` | Modified | Added PyWebView support |
| `hooks/use-websocket.ts` | Modified | Added `enabled` option |
| `app/page.tsx` | Modified | Added initialization and loading |
| `package.json` | Modified | Added static serve script |

---

## Next Phase

After completing Phase 3, proceed to **Phase 4: Build System**, which creates PyInstaller configuration and build scripts.

