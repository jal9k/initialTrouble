// hooks/use-websocket.ts

'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { ChatWebSocket } from '@/lib/websocket'
import type { ConnectionState, ServerMessage, ClientMessage, WebSocketError } from '@/types'

// ============================================================================
// Hook Options
// ============================================================================

export interface UseWebSocketOptions {
  url?: string
  autoConnect?: boolean
  reconnect?: boolean
  reconnectInterval?: number
  maxReconnectAttempts?: number
  onMessage?: (message: ServerMessage) => void
  onOpen?: () => void
  onClose?: (event: CloseEvent) => void
  onError?: (error: Event) => void
}

// ============================================================================
// Hook Return Type
// ============================================================================

export interface UseWebSocketReturn {
  // State
  isConnected: boolean
  isConnecting: boolean
  connectionState: ConnectionState
  error: WebSocketError | null
  lastMessage: ServerMessage | null

  // Derived State
  canSend: boolean
  reconnectAttempts: number

  // Actions
  connect: () => void
  disconnect: () => void
  send: (message: ClientMessage) => void
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    url,
    autoConnect = true,
    reconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
    onMessage,
    onOpen,
    onClose,
    onError
  } = options

  // State
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected')
  const [error, setError] = useState<WebSocketError | null>(null)
  const [lastMessage, setLastMessage] = useState<ServerMessage | null>(null)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)

  // Refs
  const wsRef = useRef<ChatWebSocket | null>(null)
  const callbacksRef = useRef({ onMessage, onOpen, onClose, onError })
  const setReconnectAttemptsRef = useRef(setReconnectAttempts)

  // Keep callbacks ref updated
  useEffect(() => {
    callbacksRef.current = { onMessage, onOpen, onClose, onError }
  }, [onMessage, onOpen, onClose, onError])

  // Keep setReconnectAttempts ref updated
  useEffect(() => {
    setReconnectAttemptsRef.current = setReconnectAttempts
  }, [])

  // Initialize WebSocket client
  useEffect(() => {
    wsRef.current = new ChatWebSocket({
      url,
      reconnect,
      reconnectInterval,
      maxReconnectAttempts,
      onOpen: () => {
        setConnectionState('connected')
        setError(null)
        setReconnectAttempts(0)
        callbacksRef.current.onOpen?.()
      },
      onClose: (event) => {
        setConnectionState('disconnected')
        callbacksRef.current.onClose?.(event)
      },
      onError: (event: Event) => {
        setConnectionState('error')
        const wsError: WebSocketError = {
          code: 0,
          reason: 'Connection error',
          timestamp: new Date()
        }
        setError(wsError)
        callbacksRef.current.onError?.(event)
      },
      onMessage: (message) => {
        setLastMessage(message)
        callbacksRef.current.onMessage?.(message)
      },
      onReconnect: (attempt) => {
        setReconnectAttemptsRef.current(attempt)
      }
    })

    if (autoConnect) {
      // Use a microtask to avoid calling setState during render
      queueMicrotask(() => {
        setConnectionState('connecting')
      })
      wsRef.current.connect()
    }

    return () => {
      wsRef.current?.disconnect()
    }
  }, [url, reconnect, reconnectInterval, maxReconnectAttempts, autoConnect])

  // Actions
  const connect = useCallback(() => {
    setConnectionState('connecting')
    wsRef.current?.connect()
  }, [])

  const disconnect = useCallback(() => {
    wsRef.current?.disconnect()
    setConnectionState('disconnected')
  }, [])

  const send = useCallback((message: ClientMessage) => {
    wsRef.current?.send(message)
  }, [])

  // Derived state
  const isConnected = connectionState === 'connected'
  const isConnecting = connectionState === 'connecting'
  const canSend = isConnected

  return {
    // State
    isConnected,
    isConnecting,
    connectionState,
    error,
    lastMessage,

    // Derived
    canSend,
    reconnectAttempts,

    // Actions
    connect,
    disconnect,
    send
  }
}

