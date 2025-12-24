// hooks/use-chat.ts

'use client'

import { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import { useWebSocket } from './use-websocket'
import { getSessionMessages } from '@/lib/api'
import { generateId } from '@/lib/utils'
import type {
  Message,
  ToolCall,
  ToolResult,
  ServerMessage,
  SessionOutcome
} from '@/types'

// ============================================================================
// Hook Options
// ============================================================================

export interface UseChatOptions {
  initialConversationId?: string
  onSessionStart?: (conversationId: string) => void
  onSessionEnd?: (outcome: SessionOutcome) => void
  onMessage?: (message: Message) => void
  onToolStart?: (toolCall: ToolCall) => void
  onToolComplete?: (result: ToolResult) => void
  persist?: boolean
}

// ============================================================================
// Hook Return Type
// ============================================================================

export interface UseChatReturn {
  // State
  messages: Message[]
  conversationId: string | null
  isStreaming: boolean
  isLoading: boolean
  error: Error | null
  currentToolExecution: ToolCall | null

  // Derived State
  isEmpty: boolean
  lastMessage: Message | null
  lastUserMessage: Message | null
  lastAssistantMessage: Message | null
  messageCount: number
  toolsUsed: string[]

  // Actions
  sendMessage: (content: string) => Promise<void>
  clearMessages: () => void
  loadConversation: (conversationId: string) => Promise<void>
  startNewConversation: () => void
  endConversation: (outcome: SessionOutcome) => void
  retryLastMessage: () => Promise<void>
}

// ============================================================================
// Constants
// ============================================================================

const STORAGE_KEY = 'techtime_chat'

// ============================================================================
// Hook Implementation
// ============================================================================

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

  // Refs
  const pendingMessageRef = useRef<string | null>(null)
  const callbacksRef = useRef({
    onSessionStart,
    onSessionEnd,
    onMessage,
    onToolStart,
    onToolComplete
  })

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

  // Handle incoming WebSocket messages
  const handleWebSocketMessage = useCallback(
    (serverMessage: ServerMessage) => {
      // Handle tool calls - notify for each tool that's starting
      if (serverMessage.tool_calls?.length) {
        // Track the first tool as current (UI can only show one at a time)
        setCurrentToolExecution(serverMessage.tool_calls[0])
        // But notify callbacks for ALL tool calls
        serverMessage.tool_calls.forEach((tc) => {
          callbacksRef.current.onToolStart?.(tc)
        })
      }

      // Handle response text
      if (serverMessage.response) {
        setIsStreaming(false)
        setCurrentToolExecution(null)

        const assistantMessage: Message = {
          id: generateId('msg'),
          role: 'assistant',
          content: serverMessage.response,
          timestamp: new Date(),
          toolCalls: serverMessage.tool_calls || undefined
        }

        setMessages((prev) => [...prev, assistantMessage])
        callbacksRef.current.onMessage?.(assistantMessage)

        // Tool completion is signaled when we receive a response after tool calls.
        // The actual tool results are embedded in the assistant's response text,
        // not as structured data. We signal completion with the response as result.
        if (serverMessage.tool_calls?.length) {
          serverMessage.tool_calls.forEach((tc) => {
            const result: ToolResult = {
              toolCallId: tc.id,
              name: tc.name,
              result: serverMessage.response
            }
            callbacksRef.current.onToolComplete?.(result)
          })
        }
      }

      // Update conversation ID
      if (serverMessage.conversation_id && !conversationId) {
        setConversationId(serverMessage.conversation_id)
        callbacksRef.current.onSessionStart?.(serverMessage.conversation_id)
      }
    },
    [conversationId]
  )

  // WebSocket connection
  const { send } = useWebSocket({
    onMessage: handleWebSocketMessage
  })

  // Load from localStorage on mount
  useEffect(() => {
    if (persist && !initialConversationId && typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (stored) {
          const parsed = JSON.parse(stored)
          if (parsed.messages) {
            // Convert date strings back to Date objects
            const messagesWithDates = parsed.messages.map((m: Message) => ({
              ...m,
              timestamp: new Date(m.timestamp)
            }))
            setMessages(messagesWithDates)
          }
          if (parsed.conversationId) {
            setConversationId(parsed.conversationId)
          }
        }
      } catch {
        // Ignore parse errors
      }
    }
  }, [persist, initialConversationId])

  // Save to localStorage on message changes
  useEffect(() => {
    if (persist && messages.length > 0 && typeof window !== 'undefined') {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          messages,
          conversationId
        })
      )
    }
  }, [persist, messages, conversationId])

  // Actions
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

      // Send via WebSocket
      send({
        message: content.trim(),
        conversation_id: conversationId || undefined
      })
    },
    [conversationId, send]
  )

  const clearMessages = useCallback(() => {
    setMessages([])
    setConversationId(null)
    setError(null)
    setCurrentToolExecution(null)
    if (persist && typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [persist])

  const loadConversation = useCallback(async (id: string) => {
    setIsLoading(true)
    setError(null)

    try {
      const loadedMessages = await getSessionMessages(id)
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
  }, [])

  const startNewConversation = useCallback(() => {
    clearMessages()
  }, [clearMessages])

  const endConversation = useCallback(
    (outcome: SessionOutcome) => {
      callbacksRef.current.onSessionEnd?.(outcome)
    },
    []
  )

  const retryLastMessage = useCallback(async () => {
    if (pendingMessageRef.current) {
      // Remove last assistant message if it exists
      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1]
        if (lastMsg?.role === 'assistant') {
          return prev.slice(0, -1)
        }
        return prev
      })
      await sendMessage(pendingMessageRef.current)
    }
  }, [sendMessage])

  // Derived state
  const isEmpty = messages.length === 0
  const lastMessage = messages[messages.length - 1] || null
  const lastUserMessage = useMemo(
    () => [...messages].reverse().find((m) => m.role === 'user') || null,
    [messages]
  )
  const lastAssistantMessage = useMemo(
    () => [...messages].reverse().find((m) => m.role === 'assistant') || null,
    [messages]
  )
  const messageCount = messages.length
  const toolsUsed = useMemo(() => {
    const tools = new Set<string>()
    messages.forEach((msg) => {
      msg.toolCalls?.forEach((tc) => tools.add(tc.name))
    })
    return Array.from(tools)
  }, [messages])

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

