'use client'

import { useState } from 'react'
import { cn, formatDuration } from '@/lib/utils'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger
} from '@/components/ui/collapsible'
import { Loader2, Check, X, ChevronDown, Copy } from 'lucide-react'
import type { ToolExecutionStatus, ToolExecutionCardProps } from '@/types'

const statusConfig: Record<ToolExecutionStatus, {
  icon: typeof Check | typeof X | typeof Loader2 | null
  color: string
  bg: string
  label: string
}> = {
  idle: {
    icon: null,
    color: 'border-muted',
    bg: 'bg-muted/50',
    label: 'Idle'
  },
  executing: {
    icon: Loader2,
    color: 'border-blue-500/50',
    bg: 'bg-blue-50 dark:bg-blue-950/20',
    label: 'Executing'
  },
  success: {
    icon: Check,
    color: 'border-green-500/50',
    bg: 'bg-green-50 dark:bg-green-950/20',
    label: 'Success'
  },
  error: {
    icon: X,
    color: 'border-red-500/50',
    bg: 'bg-red-50 dark:bg-red-950/20',
    label: 'Error'
  }
}

export function ToolExecutionCard({
  execution,
  onCancel,
  showDetails = false,
  className
}: ToolExecutionCardProps) {
  const [isOpen, setIsOpen] = useState(showDetails)
  const [copied, setCopied] = useState(false)

  const config = statusConfig[execution.status]
  const Icon = config.icon
  const duration = execution.startTime && execution.endTime
    ? execution.endTime.getTime() - execution.startTime.getTime()
    : null

  if (execution.status === 'idle') {
    return null
  }

  const handleCopy = async () => {
    const content = typeof execution.result === 'object'
      ? JSON.stringify(execution.result, null, 2)
      : String(execution.result)
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Card
      className={cn(
        'border transition-colors',
        config.color,
        config.bg,
        'animate-in fade-in slide-in-from-left-2 duration-200',
        className
      )}
    >
      <CardHeader className="py-3 px-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {Icon && (
              <Icon
                className={cn(
                  'h-4 w-4',
                  execution.status === 'executing' && 'animate-spin',
                  execution.status === 'success' && 'text-green-600',
                  execution.status === 'error' && 'text-red-600'
                )}
              />
            )}
            <span className="font-mono text-sm font-medium">
              {execution.toolName}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {duration !== null && (
              <Badge variant="secondary" className="text-xs">
                {formatDuration(duration)}
              </Badge>
            )}

            {execution.status === 'executing' && onCancel && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onCancel}
                className="h-6 text-xs"
              >
                Cancel
              </Button>
            )}
          </div>
        </div>

        {/* Progress bar for executing state */}
        {execution.status === 'executing' && (
          <div className="mt-2 h-1 w-full bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary animate-pulse"
              style={{
                width: '100%',
                background: 'linear-gradient(90deg, transparent, hsl(var(--primary)), transparent)',
                animation: 'shimmer 1.5s infinite'
              }}
            />
          </div>
        )}
      </CardHeader>

      {/* Result/Error content */}
      {(execution.result || execution.error) && (
        <Collapsible open={isOpen} onOpenChange={setIsOpen}>
          <CardContent className="pt-0 px-4 pb-3">
            {execution.error ? (
              <div className="text-sm text-red-600 dark:text-red-400">
                {execution.error}
              </div>
            ) : (
              <>
                <CollapsibleTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full justify-between h-8"
                  >
                    <span className="text-xs text-muted-foreground">
                      {isOpen ? 'Hide details' : 'Show details'}
                    </span>
                    <ChevronDown
                      className={cn(
                        'h-4 w-4 transition-transform',
                        isOpen && 'rotate-180'
                      )}
                    />
                  </Button>
                </CollapsibleTrigger>

                <CollapsibleContent>
                  <div className="relative mt-2">
                    <pre className="font-mono text-xs bg-muted rounded p-3 overflow-x-auto max-h-48 overflow-y-auto">
                      {typeof execution.result === 'object'
                        ? JSON.stringify(execution.result, null, 2)
                        : String(execution.result)}
                    </pre>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute top-1 right-1 h-6 w-6"
                      onClick={handleCopy}
                    >
                      {copied ? (
                        <Check className="h-3 w-3 text-green-500" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                </CollapsibleContent>
              </>
            )}
          </CardContent>
        </Collapsible>
      )}
    </Card>
  )
}

