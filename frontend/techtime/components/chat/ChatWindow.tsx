'use client'

import { useRef, useEffect, useState, useCallback } from 'react'
import { useChat, UseChatOptions } from '@/hooks/use-chat'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent } from '@/components/ui/card'
import { MessageBubble } from './MessageBubble'
import { ToolExecutionCard } from './ToolExecutionCard'
import { Send, ArrowDown, RefreshCw } from 'lucide-react'
import type { ChatWindowProps } from '@/types'

const SUGGESTIONS = [
  "My WiFi keeps disconnecting",
  "I can't access the internet",
  "DNS resolution is failing",
  "Slow network speeds"
]

interface ExtendedChatWindowProps extends ChatWindowProps, UseChatOptions {}

export function ChatWindow({ className, ...chatOptions }: ExtendedChatWindowProps) {
  const {
    messages,
    isStreaming,
    isEmpty,
    error,
    currentToolExecution,
    sendMessage,
    retryLastMessage
  } = useChat(chatOptions)

  const [input, setInput] = useState('')
  const [showScrollButton, setShowScrollButton] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const toolExecutionStartRef = useRef<Date | null>(null)

  // Track when tool execution starts (capture start time once)
  useEffect(() => {
    if (currentToolExecution && !toolExecutionStartRef.current) {
      toolExecutionStartRef.current = new Date()
    } else if (!currentToolExecution) {
      toolExecutionStartRef.current = null
    }
  }, [currentToolExecution])

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }, [messages, currentToolExecution])

  // Handle scroll position for "scroll to bottom" button
  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    const target = event.target as HTMLDivElement
    const isNearBottom = target.scrollHeight - target.scrollTop - target.clientHeight < 100
    setShowScrollButton(!isNearBottom)
  }, [])

  // Scroll to bottom handler
  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
      if (scrollContainer) {
        scrollContainer.scrollTo({
          top: scrollContainer.scrollHeight,
          behavior: 'smooth'
        })
      }
    }
  }

  // Handle send
  const handleSend = async () => {
    if (!input.trim() || isStreaming) return
    const message = input.trim()
    setInput('')
    await sendMessage(message)
  }

  // Handle key down
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Handle suggestion click
  const handleSuggestionClick = (suggestion: string) => {
    sendMessage(suggestion)
  }

  return (
    <div className={cn('flex flex-col h-full relative', className)}>
      {/* Message Area */}
      <ScrollArea
        ref={scrollAreaRef}
        className="flex-1"
        onScroll={handleScroll}
      >
        <div className="p-4 space-y-4">
          {isEmpty ? (
            // Empty state
            <div className="flex flex-col items-center justify-center h-[60vh] text-center">
              <h2 className="text-xl font-semibold mb-2">
                Network Diagnostics Assistant
              </h2>
              <p className="text-muted-foreground mb-6 max-w-md">
                I can help diagnose and troubleshoot your network issues. 
                Describe your problem or choose a common issue below.
              </p>
              <div className="grid grid-cols-2 gap-2 max-w-md">
                {SUGGESTIONS.map((suggestion) => (
                  <Button
                    key={suggestion}
                    variant="outline"
                    className="h-auto py-3 px-4 text-left"
                    onClick={() => handleSuggestionClick(suggestion)}
                  >
                    {suggestion}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            // Message list
            <>
              {messages.map((message, index) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  isLatest={index === messages.length - 1}
                />
              ))}

              {/* Tool execution */}
              {currentToolExecution && toolExecutionStartRef.current && (
                <ToolExecutionCard
                  execution={{
                    toolName: currentToolExecution.name,
                    status: 'executing',
                    startTime: toolExecutionStartRef.current
                  }}
                />
              )}

              {/* Typing indicator */}
              {isStreaming && !currentToolExecution && (
                <div className="flex items-center gap-1 p-2">
                  <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce" />
                  <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:0.1s]" />
                  <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:0.2s]" />
                </div>
              )}

              {/* Error */}
              {error && (
                <Card className="border-destructive bg-destructive/10">
                  <CardContent className="p-4 flex items-center justify-between">
                    <span className="text-destructive text-sm">
                      {error.message}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={retryLastMessage}
                    >
                      <RefreshCw className="h-4 w-4 mr-1" />
                      Retry
                    </Button>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </div>
      </ScrollArea>

      {/* Scroll to bottom button */}
      {showScrollButton && (
        <Button
          variant="secondary"
          size="icon"
          className="absolute bottom-20 right-6 rounded-full shadow-lg"
          onClick={scrollToBottom}
        >
          <ArrowDown className="h-4 w-4" />
        </Button>
      )}

      {/* Input Area */}
      <div className="border-t p-4 bg-background">
        <div className="flex gap-2">
          <Textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your network issue..."
            disabled={isStreaming}
            className="min-h-[44px] max-h-32 resize-none"
            rows={1}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            size="icon"
            className="h-[44px] w-[44px]"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

