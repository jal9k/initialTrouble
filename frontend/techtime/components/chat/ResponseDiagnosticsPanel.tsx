'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger
} from '@/components/ui/collapsible'
import { 
  ChevronDown, 
  Brain, 
  Wrench, 
  CheckCircle2, 
  XCircle, 
  AlertCircle,
  Sparkles
} from 'lucide-react'
import type { ResponseDiagnosticsPanelProps } from '@/types'

const getConfidenceColor = (score: number) => {
  if (score >= 0.7) return 'text-green-600 dark:text-green-400'
  if (score >= 0.4) return 'text-yellow-600 dark:text-yellow-400'
  return 'text-red-600 dark:text-red-400'
}

const getConfidenceLabel = (score: number) => {
  if (score >= 0.8) return 'High'
  if (score >= 0.6) return 'Medium-High'
  if (score >= 0.4) return 'Medium'
  if (score >= 0.2) return 'Low'
  return 'Very Low'
}

const getProgressColor = (score: number) => {
  if (score >= 0.7) return 'bg-green-500'
  if (score >= 0.4) return 'bg-yellow-500'
  return 'bg-red-500'
}

export function ResponseDiagnosticsPanel({
  diagnostics,
  verification,
  defaultExpanded = true,
  className
}: ResponseDiagnosticsPanelProps) {
  const [isOpen, setIsOpen] = useState(defaultExpanded)

  const confidencePercent = Math.round(diagnostics.confidenceScore * 100)
  const hasTools = diagnostics.toolsUsed.length > 0
  const hasThoughts = diagnostics.thoughts.length > 0

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <Card
        className={cn(
          'border border-muted bg-muted/30 mt-2',
          'animate-in fade-in slide-in-from-bottom-1 duration-200',
          className
        )}
      >
        <CollapsibleTrigger asChild>
          <CardHeader className="py-2 px-3 cursor-pointer hover:bg-muted/50 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Response Diagnostics</span>
              </div>
              <div className="flex items-center gap-3">
                {/* Confidence indicator */}
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground">Confidence:</span>
                  <span className={cn('text-xs font-medium', getConfidenceColor(diagnostics.confidenceScore))}>
                    {confidencePercent}%
                  </span>
                </div>
                
                {/* Tools count badge */}
                {hasTools && (
                  <Badge variant="secondary" className="text-xs">
                    {diagnostics.toolsUsed.length} tool{diagnostics.toolsUsed.length !== 1 ? 's' : ''}
                  </Badge>
                )}
                
                {/* Verification badge */}
                {verification && (
                  <Badge 
                    variant={verification.passed ? 'default' : 'destructive'}
                    className="text-xs"
                  >
                    {verification.passed ? 'Verified' : 'Verification Failed'}
                  </Badge>
                )}
                
                <ChevronDown
                  className={cn(
                    'h-4 w-4 text-muted-foreground transition-transform',
                    isOpen && 'rotate-180'
                  )}
                />
              </div>
            </div>
          </CardHeader>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <CardContent className="pt-0 px-3 pb-3 space-y-4">
            {/* Confidence Score */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Confidence Score</span>
                <span className={cn('font-medium', getConfidenceColor(diagnostics.confidenceScore))}>
                  {getConfidenceLabel(diagnostics.confidenceScore)} ({confidencePercent}%)
                </span>
              </div>
              <div className="relative h-2 w-full bg-muted rounded-full overflow-hidden">
                <div
                  className={cn('h-full transition-all duration-300', getProgressColor(diagnostics.confidenceScore))}
                  style={{ width: `${confidencePercent}%` }}
                />
              </div>
            </div>

            {/* Verification Result */}
            {verification && (
              <div className={cn(
                'p-2 rounded-md text-sm',
                verification.passed 
                  ? 'bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300'
                  : 'bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300'
              )}>
                <div className="flex items-center gap-2">
                  {verification.passed ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    <AlertCircle className="h-4 w-4" />
                  )}
                  <span className="font-medium">
                    {verification.passed ? 'Fix Verified' : 'Verification Failed'}
                  </span>
                </div>
                {verification.message && (
                  <p className="mt-1 text-xs opacity-80">{verification.message}</p>
                )}
              </div>
            )}

            {/* Tools Used */}
            {hasTools && (
              <div className="space-y-2">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Wrench className="h-3.5 w-3.5" />
                  <span>Tools Used</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {diagnostics.toolsUsed.map((tool, idx) => (
                    <Badge
                      key={`${tool.name}-${idx}`}
                      variant="outline"
                      className={cn(
                        'text-xs font-mono gap-1',
                        tool.success 
                          ? 'border-green-500/50 text-green-700 dark:text-green-300'
                          : 'border-red-500/50 text-red-700 dark:text-red-300'
                      )}
                    >
                      {tool.success ? (
                        <CheckCircle2 className="h-3 w-3" />
                      ) : (
                        <XCircle className="h-3 w-3" />
                      )}
                      {tool.name}
                      {tool.durationMs !== undefined && (
                        <span className="text-muted-foreground">
                          ({tool.durationMs}ms)
                        </span>
                      )}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Thoughts/Reasoning */}
            {hasThoughts && (
              <div className="space-y-2">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Brain className="h-3.5 w-3.5" />
                  <span>Reasoning</span>
                </div>
                <ul className="space-y-1 text-xs text-muted-foreground">
                  {diagnostics.thoughts.map((thought, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-muted-foreground/50 select-none">•</span>
                      <span>{thought}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  )
}

