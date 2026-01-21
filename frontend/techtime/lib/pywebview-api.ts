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
  SessionOutcome,
  ProviderInfo,
  OllamaModelInfo,
  ProviderName
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

import { PYWEBVIEW_TIMEOUT } from './constants'

/**
 * Wait for PyWebView API to become available.
 * In desktop mode, there's a brief moment after page load before the API is ready.
 */
export async function waitForPyWebView(
  timeoutMs: number = PYWEBVIEW_TIMEOUT
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
      onStatus?: (status: { 
        phase: 'thinking' | 'tool_execution' | 'generating'
        iteration: number
        totalIterations?: number
        message: string 
      }) => void
      onDone?: (finalContent: string, evalStats?: {
        totalDurationMs?: number
        tokensInfo?: string
        model?: string
        toolTotalMs?: number
        toolCount?: number
      }) => void
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
        case 'status':
          callbacks.onStatus?.({
            phase: chunk.data.phase as 'thinking' | 'tool_execution' | 'generating',
            iteration: chunk.data.iteration as number,
            totalIterations: chunk.data.total_iterations as number | undefined,
            message: chunk.data.message as string
          })
          break
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
        case 'done': {
          const evalStats = chunk.data.eval_stats as Record<string, unknown> | undefined
          callbacks.onDone?.(
            chunk.data.final as string,
            evalStats ? {
              totalDurationMs: evalStats.total_duration_ms as number | undefined,
              tokensInfo: evalStats.tokens_info as string | undefined,
              model: evalStats.model as string | undefined,
              toolTotalMs: evalStats.tool_total_ms as number | undefined,
              toolCount: evalStats.tool_count as number | undefined,
            } : undefined
          )
          break
        }
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
        displayName: t.name, // PyWebView API doesn't include displayName
        description: t.description,
        category: 'system' as const, // Default category
        parameters: t.parameters.map((p) => ({
          name: p.name,
          type: p.type as 'string' | 'number' | 'boolean' | 'array',
          description: p.description,
          required: p.required
        })),
        osiLayer: 1 // Default OSI layer
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

  /**
   * Get available LLM providers with their models.
   */
  async getAvailableProviders(): Promise<{
    online: boolean
    providers: Record<string, ProviderInfo>
    ollamaModels: OllamaModelInfo[]
  }> {
    if (isDesktopMode()) {
      const result = await pywebviewCall(() =>
        window.pywebview!.api.get_available_providers()
      )
      return {
        online: result.online,
        providers: Object.fromEntries(
          Object.entries(result.providers).map(([name, info]) => [
            name,
            {
              available: info.available,
              model: info.model,
              type: info.type === 'local' ? 'local' : 'cloud'
            } as ProviderInfo
          ])
        ),
        ollamaModels: result.ollama_models.map((m) => ({
          name: m.name,
          size: m.size,
          modified_at: m.modified_at
        }))
      }
    }

    // HTTP mode - use the HTTP API
    const result = await httpApi.getAvailableProviders()
    return {
      online: result.online,
      providers: result.providers,
      ollamaModels: result.ollama_models
    }
  },

  /**
   * Set the active LLM provider and model.
   */
  async setActiveModel(
    provider: ProviderName,
    model?: string
  ): Promise<{ provider: string; model: string }> {
    if (isDesktopMode()) {
      const result = await pywebviewCall(() =>
        window.pywebview!.api.set_active_model(provider, model ?? null)
      )
      return {
        provider: result.provider,
        model: result.model
      }
    }

    // HTTP mode
    const result = await httpApi.selectModel(provider, model)
    return {
      provider: result.provider,
      model: result.model
    }
  },

  /**
   * Get the currently active LLM provider and model.
   */
  async getActiveModel(): Promise<{ provider: string; model: string }> {
    if (isDesktopMode()) {
      const result = await pywebviewCall(() =>
        window.pywebview!.api.get_active_model()
      )
      return {
        provider: result.provider,
        model: result.model
      }
    }

    // HTTP mode - get from health endpoint
    const health = await httpApi.getHealth()
    return {
      provider: health.active_provider || 'ollama',
      model: health.active_model || 'unknown'
    }
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
        resolutionRate: summary.resolved_count / (summary.total_sessions || 1),
        averageTimeToResolution: summary.avg_messages_per_session,
        totalCost: summary.total_cost_usd
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
        executionCount: s.total_calls,
        successRate: s.success_count / (s.total_calls || 1),
        averageDuration: s.avg_execution_time_ms,
        lastUsed: new Date()
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

