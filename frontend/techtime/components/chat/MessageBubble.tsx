'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn, formatDate } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Check, Copy, Zap } from 'lucide-react'
import type { MessageBubbleProps } from '@/types'

const roleStyles: Record<string, string> = {
  user: 'ml-auto bg-primary text-primary-foreground rounded-2xl rounded-br-md',
  assistant: 'mr-auto bg-muted rounded-2xl rounded-bl-md',
  system: 'mx-auto text-muted-foreground text-sm text-center italic',
  tool: 'mr-auto bg-muted/50 border rounded-lg font-mono text-sm'
}

export function MessageBubble({
  message,
  isLatest = false,
  showTimestamp = true,
  className
}: MessageBubbleProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const showCopyButton = message.role === 'assistant'
  const shouldRenderMarkdown = message.role === 'assistant'

  return (
    <div
      className={cn(
        'group flex flex-col',
        message.role === 'user' ? 'items-end' : 'items-start',
        isLatest && 'animate-in fade-in slide-in-from-bottom-2 duration-200',
        className
      )}
    >
      {/* Tool indicator */}
      {message.role === 'tool' && message.toolResult && (
        <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
          <Zap className="h-3 w-3" />
          <span>{message.toolResult.name}</span>
        </div>
      )}

      {/* Message bubble */}
      <div
        className={cn(
          'px-4 py-2 max-w-[80%]',
          roleStyles[message.role]
        )}
      >
        {shouldRenderMarkdown ? (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ href, children }) => (
                  <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary underline">
                    {children}
                  </a>
                ),
                code: ({ className, children, ...props }) => {
                  const isInline = !className
                  if (isInline) {
                    return (
                      <code className="bg-muted px-1 py-0.5 rounded text-sm" {...props}>
                        {children}
                      </code>
                    )
                  }
                  return (
                    <pre className="bg-muted rounded-md p-3 overflow-x-auto">
                      <code className={className} {...props}>{children}</code>
                    </pre>
                  )
                }
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        ) : (
          <p className="whitespace-pre-wrap">{message.content}</p>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center gap-2 mt-1 px-1">
        {showTimestamp && (
          <span className="text-xs text-muted-foreground">
            {formatDate(message.timestamp, 'time')}
          </span>
        )}

        {showCopyButton && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={handleCopy}
              >
                {copied ? (
                  <Check className="h-3 w-3 text-green-500" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              {copied ? 'Copied!' : 'Copy message'}
            </TooltipContent>
          </Tooltip>
        )}
      </div>

      {/* Tool calls indicator */}
      {message.toolCalls && message.toolCalls.length > 0 && (
        <div className="mt-2 text-xs text-muted-foreground">
          Used: {message.toolCalls.map(tc => tc.name).join(', ')}
        </div>
      )}
    </div>
  )
}

