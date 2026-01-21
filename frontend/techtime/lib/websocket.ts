// lib/websocket.ts

import type { ClientMessage, ServerMessage, ConnectionState } from '@/types'
import { WS_RECONNECT_INTERVAL, WS_MAX_RECONNECT_ATTEMPTS } from './constants'

// ============================================================================
// Configuration
// ============================================================================

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'
const WS_ENDPOINT = '/ws'

export interface WebSocketConfig {
  url?: string
  reconnect?: boolean
  reconnectInterval?: number
  maxReconnectAttempts?: number
  onOpen?: () => void
  onClose?: (event: CloseEvent) => void
  onError?: (error: Event) => void
  onMessage?: (message: ServerMessage) => void
  onReconnect?: (attempt: number) => void
}

const DEFAULT_CONFIG = {
  url: `${WS_BASE_URL}${WS_ENDPOINT}`,
  reconnect: true,
  reconnectInterval: WS_RECONNECT_INTERVAL,
  maxReconnectAttempts: WS_MAX_RECONNECT_ATTEMPTS
}

// ============================================================================
// WebSocket Client Class
// ============================================================================

export class ChatWebSocket {
  private socket: WebSocket | null = null
  private config: Required<WebSocketConfig>
  private reconnectAttempts = 0
  private reconnectTimeout: NodeJS.Timeout | null = null
  private messageQueue: ClientMessage[] = []

  constructor(config: WebSocketConfig = {}) {
    // Only include defined config values to avoid overwriting defaults with undefined
    const definedConfig: Partial<WebSocketConfig> = {}
    if (config.url !== undefined) definedConfig.url = config.url
    if (config.reconnect !== undefined) definedConfig.reconnect = config.reconnect
    if (config.reconnectInterval !== undefined) definedConfig.reconnectInterval = config.reconnectInterval
    if (config.maxReconnectAttempts !== undefined) definedConfig.maxReconnectAttempts = config.maxReconnectAttempts
    
    this.config = {
      ...DEFAULT_CONFIG,
      ...definedConfig,
      onOpen: config.onOpen || (() => {}),
      onClose: config.onClose || (() => {}),
      onError: config.onError || (() => {}),
      onMessage: config.onMessage || (() => {}),
      onReconnect: config.onReconnect || (() => {})
    } as Required<WebSocketConfig>
  }

  get state(): ConnectionState {
    if (!this.socket) return 'disconnected'

    switch (this.socket.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting'
      case WebSocket.OPEN:
        return 'connected'
      case WebSocket.CLOSING:
      case WebSocket.CLOSED:
      default:
        return 'disconnected'
    }
  }

  get isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN
  }

  connect(): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      this.socket = new WebSocket(this.config.url)

      this.socket.onopen = () => {
        this.reconnectAttempts = 0
        this.flushMessageQueue()
        this.config.onOpen()
      }

      this.socket.onclose = (event) => {
        this.config.onClose(event)
        if (event.code !== 1000) {
          this.handleReconnect()
        }
      }

      this.socket.onerror = (error) => {
        this.config.onError(error)
      }

      this.socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as ServerMessage
          this.config.onMessage(message)
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }
    } catch (err) {
      console.error('Failed to create WebSocket:', err)
    }
  }

  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }

    if (this.socket) {
      this.socket.close(1000, 'Client disconnect')
      this.socket = null
    }
  }

  send(message: ClientMessage): void {
    if (this.isConnected) {
      this.socket!.send(JSON.stringify(message))
    } else {
      this.messageQueue.push(message)
      if (this.state === 'disconnected') {
        this.connect()
      }
    }
  }

  private handleReconnect(): void {
    if (!this.config.reconnect) return
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }

    this.reconnectAttempts++
    this.config.onReconnect(this.reconnectAttempts)

    this.reconnectTimeout = setTimeout(() => {
      this.connect()
    }, this.config.reconnectInterval)
  }

  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift()!
      this.send(message)
    }
  }
}

// ============================================================================
// Singleton Pattern
// ============================================================================

let instance: ChatWebSocket | null = null

export function getWebSocket(config?: WebSocketConfig): ChatWebSocket {
  if (!instance) {
    instance = new ChatWebSocket(config)
  }
  return instance
}

export function destroyWebSocket(): void {
  if (instance) {
    instance.disconnect()
    instance = null
  }
}

