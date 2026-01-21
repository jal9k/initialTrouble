# REST API Client

This document specifies the REST API client for communicating with the Python backend.

## File Location

```
frontend/
  lib/
    api.ts          # REST API client
```

---

## Overview

The API client provides typed functions for all REST endpoints. It handles:
- Base URL configuration
- Request/response serialization
- Error handling
- Response type validation

---

## Configuration

```typescript
// lib/api.ts

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface RequestConfig {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
  headers?: Record<string, string>
  cache?: RequestCache
  revalidate?: number
}
```

---

## Core Functions

### Base Request Function

```typescript
/**
 * Base fetch wrapper with error handling
 */
async function apiRequest<T>(
  endpoint: string,
  config: RequestConfig = {}
): Promise<T> {
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
```

### Error Class

```typescript
/**
 * Custom API error class
 */
class ApiError extends Error {
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
```

---

## API Functions

### Health Check

```typescript
/**
 * Check backend health status
 */
async function getHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>('/health')
}
```

### Sessions API

```typescript
/**
 * List sessions with optional filters
 */
interface ListSessionsParams {
  page?: number
  pageSize?: number
  outcome?: SessionOutcome
  startDate?: Date
  endDate?: Date
}

async function listSessions(
  params: ListSessionsParams = {}
): Promise<PaginatedResponse<SessionListItem>> {
  const searchParams = new URLSearchParams()
  
  if (params.page) searchParams.set('page', String(params.page))
  if (params.pageSize) searchParams.set('page_size', String(params.pageSize))
  if (params.outcome) searchParams.set('outcome', params.outcome)
  if (params.startDate) searchParams.set('start_date', params.startDate.toISOString())
  if (params.endDate) searchParams.set('end_date', params.endDate.toISOString())
  
  const query = searchParams.toString()
  return apiRequest<PaginatedResponse<SessionListItem>>(
    `/api/sessions${query ? `?${query}` : ''}`
  )
}

/**
 * Get session details by ID
 */
async function getSession(id: string): Promise<Session> {
  return apiRequest<Session>(`/api/sessions/${id}`)
}

/**
 * Get session messages
 */
async function getSessionMessages(id: string): Promise<Message[]> {
  return apiRequest<Message[]>(`/api/sessions/${id}/messages`)
}
```

### Analytics API

```typescript
/**
 * Get analytics summary
 */
interface AnalyticsSummaryParams {
  startDate?: Date
  endDate?: Date
}

async function getAnalyticsSummary(
  params: AnalyticsSummaryParams = {}
): Promise<SessionSummary> {
  const searchParams = new URLSearchParams()
  
  if (params.startDate) searchParams.set('start_date', params.startDate.toISOString())
  if (params.endDate) searchParams.set('end_date', params.endDate.toISOString())
  
  const query = searchParams.toString()
  return apiRequest<SessionSummary>(
    `/api/analytics/summary${query ? `?${query}` : ''}`
  )
}

/**
 * Get tool statistics
 */
async function getToolStats(): Promise<ToolStats[]> {
  return apiRequest<ToolStats[]>('/api/analytics/tools')
}

/**
 * Get sessions over time
 */
interface SessionsOverTimeParams {
  startDate: Date
  endDate: Date
  granularity?: 'hour' | 'day' | 'week'
}

async function getSessionsOverTime(
  params: SessionsOverTimeParams
): Promise<TimeSeriesPoint[]> {
  const searchParams = new URLSearchParams({
    start_date: params.startDate.toISOString(),
    end_date: params.endDate.toISOString(),
    granularity: params.granularity || 'day'
  })
  
  return apiRequest<TimeSeriesPoint[]>(
    `/api/analytics/sessions-over-time?${searchParams}`
  )
}

/**
 * Get issue category breakdown
 */
async function getCategoryBreakdown(): Promise<CategoryBreakdown[]> {
  return apiRequest<CategoryBreakdown[]>('/api/analytics/categories')
}
```

### Tools API

```typescript
/**
 * List available diagnostic tools
 */
async function listTools(): Promise<DiagnosticTool[]> {
  return apiRequest<DiagnosticTool[]>('/api/tools')
}

/**
 * Execute a diagnostic tool directly
 */
interface ExecuteToolParams {
  toolName: string
  parameters?: Record<string, unknown>
}

async function executeTool(
  params: ExecuteToolParams
): Promise<ToolResult> {
  return apiRequest<ToolResult>(`/api/tools/${params.toolName}/execute`, {
    method: 'POST',
    body: params.parameters || {}
  })
}
```

---

## Export Pattern

```typescript
// lib/api.ts

export {
  // Error class
  ApiError,
  
  // Health
  getHealth,
  
  // Sessions
  listSessions,
  getSession,
  getSessionMessages,
  
  // Analytics
  getAnalyticsSummary,
  getToolStats,
  getSessionsOverTime,
  getCategoryBreakdown,
  
  // Tools
  listTools,
  executeTool
}

export type {
  ListSessionsParams,
  AnalyticsSummaryParams,
  SessionsOverTimeParams,
  ExecuteToolParams
}
```

---

## Usage Examples

### In Server Components

```typescript
// app/dashboard/page.tsx
import { getAnalyticsSummary, getToolStats } from '@/lib/api'

export default async function DashboardPage() {
  const [summary, toolStats] = await Promise.all([
    getAnalyticsSummary(),
    getToolStats()
  ])
  
  return (
    <div>
      <SummaryCards summary={summary} />
      <ToolStatsTable stats={toolStats} />
    </div>
  )
}
```

### In Client Components

```typescript
'use client'

import { useState, useEffect } from 'react'
import { listSessions, ApiError } from '@/lib/api'

export function SessionList() {
  const [sessions, setSessions] = useState([])
  const [error, setError] = useState<string | null>(null)
  
  useEffect(() => {
    listSessions({ pageSize: 10 })
      .then(res => setSessions(res.items))
      .catch(err => {
        if (err instanceof ApiError) {
          setError(err.message)
        }
      })
  }, [])
  
  // ...
}
```

### With Error Handling

```typescript
import { getSession, ApiError } from '@/lib/api'
import { notFound } from 'next/navigation'

export default async function SessionPage({ params }: { params: { id: string } }) {
  try {
    const session = await getSession(params.id)
    return <SessionDetails session={session} />
  } catch (err) {
    if (err instanceof ApiError && err.isNotFound) {
      notFound()
    }
    throw err
  }
}
```

---

## Error Handling Strategy

| Status Code | Handling |
|-------------|----------|
| 400 | Show validation error message |
| 401 | Redirect to login (if auth implemented) |
| 404 | Show not found page or component |
| 429 | Show rate limit message, retry after delay |
| 500+ | Show generic error, log to monitoring |

---

## Test Specifications

### Unit Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| `apiRequest` adds correct headers | Content-Type: application/json set |
| `apiRequest` handles JSON body | Body serialized correctly |
| `ApiError` created on non-ok response | Error contains status and message |
| `ApiError.isNotFound` returns true for 404 | Property correctly identifies status |

### Integration Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| `getHealth` returns health status | Response matches HealthResponse type |
| `listSessions` returns paginated list | Response matches PaginatedResponse type |
| `executeTool` sends parameters | Server receives correct payload |

### Mock Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Network error handled | Throws with appropriate message |
| Timeout handled | Request fails after timeout period |
| Retry logic works | Failed requests retried (if implemented) |

---

## Lint/Build Verification

- [ ] All functions properly typed
- [ ] Error class extends Error correctly
- [ ] No any types used
- [ ] All API responses typed
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] Unit tests pass

---

## Related Documents

- [interfaces.md](../types/interfaces.md) - Type definitions
- [websocket.md](./websocket.md) - WebSocket client
- [use-chat.md](../hooks/use-chat.md) - Uses API for session loading

