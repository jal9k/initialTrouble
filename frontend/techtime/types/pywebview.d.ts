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
declare global {
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
}

export type {
  ApiResponse,
  ModelProgress,
  StreamChunk,
  ChatResponse,
  SessionListResponse,
  MessageResponse,
  ToolDefinition,
  ToolExecutionResult,
  ModelInfo,
  AppInfo,
  AnalyticsSummaryResponse,
  ToolStatsResponse,
  PyWebViewApi,
  PyWebView
}

