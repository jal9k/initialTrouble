// lib/api.ts

import type {
  HealthResponse,
  SessionListItem,
  Session,
  Message,
  SessionSummary,
  ToolStats,
  TimeSeriesPoint,
  CategoryBreakdown,
  DiagnosticTool,
  ToolResult,
  PaginatedResponse,
  SessionOutcome,
  IssueCategory,
  ProviderInfo,
  OllamaModelInfo,
  ProviderName
} from '@/types'

// ============================================================================
// Configuration
// ============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface RequestConfig {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  body?: unknown
  headers?: Record<string, string>
  cache?: RequestCache
  revalidate?: number
}

// ============================================================================
// Error Handling
// ============================================================================

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message)
    this.name = 'ApiError'
  }

  get isNotFound(): boolean {
    return this.status === 404
  }

  get isUnauthorized(): boolean {
    return this.status === 401
  }

  get isServerError(): boolean {
    return this.status >= 500
  }
}

// ============================================================================
// Base Request Function
// ============================================================================

async function apiRequest<T>(endpoint: string, config: RequestConfig = {}): Promise<T> {
  const { method = 'GET', body, headers = {}, cache, revalidate } = config

  const url = `${API_BASE_URL}${endpoint}`

  const response = await fetch(url, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers
    },
    body: body ? JSON.stringify(body) : undefined,
    cache,
    next: revalidate ? { revalidate } : undefined
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new ApiError(response.status, error.detail || 'Request failed')
  }

  return response.json()
}

// ============================================================================
// Health
// ============================================================================

export async function getHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>('/health')
}

// ============================================================================
// LLM Provider Management
// ============================================================================

interface OllamaModelsApiResponse {
  models: Array<{
    name: string
    size: number
    modified_at: string
  }>
}

export async function getOllamaModels(): Promise<OllamaModelInfo[]> {
  const response = await apiRequest<OllamaModelsApiResponse>('/api/models/ollama')
  return response.models.map(m => ({
    name: m.name,
    size: m.size,
    modified_at: m.modified_at
  }))
}

export interface ProvidersResponse {
  online: boolean
  providers: Record<string, ProviderInfo>
  ollama_models: OllamaModelInfo[]
}

export async function getAvailableProviders(): Promise<ProvidersResponse> {
  // Fetch health to get provider status
  const health = await getHealth()
  
  // Fetch ollama models
  let ollamaModels: OllamaModelInfo[] = []
  try {
    ollamaModels = await getOllamaModels()
  } catch {
    // Ollama might not be running
  }
  
  // Build providers from health response
  const providers: Record<string, ProviderInfo> = {}
  if (health.providers) {
    for (const [name, info] of Object.entries(health.providers)) {
      providers[name] = {
        available: info.available,
        model: info.model,
        type: name === 'ollama' ? 'local' : 'cloud'
      }
    }
  }
  
  return {
    online: health.llm_backends?.online ?? false,
    providers,
    ollama_models: ollamaModels
  }
}

interface SelectModelRequest {
  provider: string
  model?: string
}

interface SelectModelResponse {
  success: boolean
  provider: string
  model: string
  message?: string
}

export async function selectModel(provider: ProviderName, model?: string): Promise<SelectModelResponse> {
  const body: SelectModelRequest = { provider }
  if (model) {
    body.model = model
  }
  
  return apiRequest<SelectModelResponse>('/api/model/select', {
    method: 'POST',
    body
  })
}

// ============================================================================
// Sessions
// ============================================================================

export interface ListSessionsParams {
  page?: number
  pageSize?: number
  outcome?: SessionOutcome
  category?: IssueCategory
  startDate?: Date
  endDate?: Date
}

interface ApiSessionListItem {
  id: string
  startTime: string
  outcome: SessionOutcome
  issueCategory?: string | null
  preview: string
}

interface ApiPaginatedSessions {
  items: ApiSessionListItem[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}

export async function listSessions(
  params: ListSessionsParams = {}
): Promise<PaginatedResponse<SessionListItem>> {
  const searchParams = new URLSearchParams()

  if (params.page) searchParams.set('page', String(params.page))
  if (params.pageSize) searchParams.set('page_size', String(params.pageSize))
  if (params.outcome) searchParams.set('outcome', params.outcome)
  if (params.category) searchParams.set('category', params.category)
  if (params.startDate) searchParams.set('start_date', params.startDate.toISOString())
  if (params.endDate) searchParams.set('end_date', params.endDate.toISOString())

  const query = searchParams.toString()
  const response = await apiRequest<ApiPaginatedSessions>(
    `/api/sessions${query ? `?${query}` : ''}`,
    { cache: 'no-store' }
  )
  
  // Convert string timestamps to Date objects and map issueCategory
  return {
    ...response,
    items: response.items.map(item => ({
      id: item.id,
      startTime: new Date(item.startTime),
      outcome: item.outcome,
      issueCategory: item.issueCategory as SessionListItem['issueCategory'],
      preview: item.preview
    }))
  }
}

export async function getSession(id: string): Promise<Session> {
  return apiRequest<Session>(`/api/sessions/${id}`)
}

export async function getSessionMessages(id: string): Promise<Message[]> {
  return apiRequest<Message[]>(`/api/sessions/${id}/messages`)
}

export async function deleteSession(id: string): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(`/api/sessions/${id}`, {
    method: 'DELETE'
  })
}

export interface UpdateSessionParams {
  preview?: string
  outcome?: string
}

export interface UpdateSessionResponse {
  success: boolean
  preview_updated?: boolean | null
  outcome_updated?: boolean | null
}

export async function updateSession(
  id: string,
  params: UpdateSessionParams
): Promise<UpdateSessionResponse> {
  return apiRequest<UpdateSessionResponse>(`/api/sessions/${id}`, {
    method: 'PATCH',
    body: params
  })
}

// ============================================================================
// Analytics
// ============================================================================

export interface AnalyticsSummaryParams {
  startDate?: Date
  endDate?: Date
}

interface ApiSummaryResponse {
  totalSessions: number
  resolvedCount: number
  unresolvedCount: number
  abandonedCount: number
  resolutionRate: number
  averageTimeToResolution: number
  totalCost: number
}

export async function getAnalyticsSummary(
  params: AnalyticsSummaryParams = {}
): Promise<SessionSummary> {
  const searchParams = new URLSearchParams()

  if (params.startDate) searchParams.set('start_date', params.startDate.toISOString())
  if (params.endDate) searchParams.set('end_date', params.endDate.toISOString())

  const query = searchParams.toString()
  const response = await apiRequest<ApiSummaryResponse>(
    `/api/analytics/frontend/summary${query ? `?${query}` : ''}`
  )
  
  return {
    totalSessions: response.totalSessions,
    resolvedCount: response.resolvedCount,
    unresolvedCount: response.unresolvedCount,
    abandonedCount: response.abandonedCount,
    resolutionRate: response.resolutionRate,
    averageTimeToResolution: response.averageTimeToResolution,
    totalCost: response.totalCost
  }
}

interface ApiToolStatsItem {
  toolName: string
  executionCount: number
  successRate: number
  averageDuration: number
  lastUsed: string
}

export async function getToolStats(): Promise<ToolStats[]> {
  const response = await apiRequest<ApiToolStatsItem[]>('/api/analytics/frontend/tools')
  return response.map(item => ({
    toolName: item.toolName,
    executionCount: item.executionCount,
    // Backend returns percentage (0-100), frontend expects ratio (0-1)
    successRate: item.successRate / 100,
    averageDuration: item.averageDuration,
    lastUsed: new Date(item.lastUsed)
  }))
}

export interface SessionsOverTimeParams {
  startDate: Date
  endDate: Date
  granularity?: 'hour' | 'day' | 'week'
}

interface ApiTimeSeriesPoint {
  timestamp: string
  value: number
}

export async function getSessionsOverTime(
  params: SessionsOverTimeParams
): Promise<TimeSeriesPoint[]> {
  const searchParams = new URLSearchParams({
    start_date: params.startDate.toISOString(),
    end_date: params.endDate.toISOString(),
    granularity: params.granularity || 'day'
  })

  const response = await apiRequest<ApiTimeSeriesPoint[]>(
    `/api/analytics/sessions-over-time?${searchParams}`
  )
  return response.map(point => ({
    timestamp: new Date(point.timestamp),
    value: point.value
  }))
}

interface ApiCategoryItem {
  category: string
  count: number
  percentage: number
}

export async function getCategoryBreakdown(): Promise<CategoryBreakdown[]> {
  const response = await apiRequest<ApiCategoryItem[]>('/api/analytics/categories')
  return response.map(item => ({
    category: item.category,
    count: item.count,
    percentage: item.percentage
  }))
}

// ============================================================================
// Tools
// ============================================================================

export async function listTools(): Promise<DiagnosticTool[]> {
  return apiRequest<DiagnosticTool[]>('/api/tools')
}

export interface ExecuteToolParams {
  toolName: string
  parameters?: Record<string, unknown>
}

export async function executeTool(params: ExecuteToolParams): Promise<ToolResult> {
  return apiRequest<ToolResult>(`/api/tools/${params.toolName}/execute`, {
    method: 'POST',
    body: params.parameters || {}
  })
}

