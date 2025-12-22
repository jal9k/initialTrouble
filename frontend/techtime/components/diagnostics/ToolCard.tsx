'use client'

import { useState, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger
} from '@/components/ui/collapsible'
import { ChevronDown, Loader2, Play, Zap } from 'lucide-react'
import type { ToolParameter, ToolCardProps } from '@/types'

interface ParameterInputProps {
  param: ToolParameter
  value: unknown
  onChange: (value: unknown) => void
  disabled: boolean
}

function ParameterInput({
  param,
  value,
  onChange,
  disabled
}: ParameterInputProps) {
  switch (param.type) {
    case 'boolean':
      return (
        <Switch
          checked={Boolean(value)}
          onCheckedChange={onChange}
          disabled={disabled}
        />
      )
    case 'number':
      return (
        <Input
          type="number"
          value={value as number || ''}
          onChange={(e) => onChange(Number(e.target.value))}
          disabled={disabled}
          placeholder={String(param.default || '')}
        />
      )
    case 'array':
      // Handle array as comma-separated values
      return (
        <Input
          type="text"
          value={Array.isArray(value) ? value.join(', ') : (value as string || '')}
          onChange={(e) => {
            const inputValue = e.target.value
            if (inputValue.trim() === '') {
              onChange(undefined)
            } else {
              // Split by comma and trim whitespace
              const arrayValue = inputValue.split(',').map(s => s.trim()).filter(Boolean)
              onChange(arrayValue)
            }
          }}
          disabled={disabled}
          placeholder="value1, value2, ..."
        />
      )
    case 'string':
    default:
      return (
        <Input
          type="text"
          value={value as string || ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder={String(param.default || '')}
        />
      )
  }
}

export function ToolCard({
  tool,
  isExpanded,
  isExecuting,
  onToggle,
  onExecute,
  lastResult,
  className
}: ToolCardProps) {
  const [params, setParams] = useState<Record<string, unknown>>(() => {
    // Initialize with defaults
    const defaults: Record<string, unknown> = {}
    tool.parameters.forEach(p => {
      if (p.default !== undefined) {
        defaults[p.name] = p.default
      }
    })
    return defaults
  })

  const handleParamChange = useCallback((name: string, value: unknown) => {
    setParams(prev => ({ ...prev, [name]: value }))
  }, [])

  const handleExecute = () => {
    // Validate required params
    const missingRequired = tool.parameters
      .filter(p => p.required && params[p.name] === undefined)
      .map(p => p.name)

    if (missingRequired.length > 0) {
      console.error('Missing required params:', missingRequired)
      return
    }

    onExecute(params)
  }

  const hasParameters = tool.parameters.length > 0

  return (
    <Card className={cn('overflow-hidden', className)}>
      <Collapsible open={isExpanded} onOpenChange={onToggle}>
        {/* Header */}
        <CollapsibleTrigger asChild>
          <div className="flex items-center justify-between p-3 cursor-pointer hover:bg-muted/50 transition-colors">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-muted-foreground" />
              <span className="font-mono text-sm font-medium">
                {tool.name}
              </span>
              <Badge variant="secondary" className="text-xs">
                {tool.category}
              </Badge>
            </div>
            <ChevronDown
              className={cn(
                'h-4 w-4 text-muted-foreground transition-transform',
                isExpanded && 'rotate-180'
              )}
            />
          </div>
        </CollapsibleTrigger>

        {/* Description (always visible) */}
        <div className="px-3 pb-3">
          <p className="text-sm text-muted-foreground">
            {tool.description}
          </p>
        </div>

        {/* Expanded content */}
        <CollapsibleContent>
          <div className="px-3 pb-4 space-y-4 border-t pt-3">
            {/* Parameters */}
            {hasParameters && (
              <div className="space-y-3">
                <h4 className="text-sm font-medium">Parameters</h4>
                <div className="grid gap-3">
                  {tool.parameters.map(param => (
                    <div key={param.name} className="space-y-1">
                      <Label className="text-xs flex items-center gap-1">
                        {param.name}
                        {param.required && (
                          <span className="text-destructive">*</span>
                        )}
                      </Label>
                      <ParameterInput
                        param={param}
                        value={params[param.name]}
                        onChange={(v) => handleParamChange(param.name, v)}
                        disabled={isExecuting}
                      />
                      <p className="text-xs text-muted-foreground">
                        {param.description}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Execute button */}
            <Button
              onClick={handleExecute}
              disabled={isExecuting}
              className="w-full"
            >
              {isExecuting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Executing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Execute
                </>
              )}
            </Button>

            {/* Last result */}
            {lastResult && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Last Result</h4>
                <div className="bg-muted rounded-md p-3 font-mono text-xs max-h-48 overflow-auto">
                  {lastResult.error ? (
                    <span className="text-destructive">{lastResult.error}</span>
                  ) : (
                    <pre>
                      {typeof lastResult.result === 'object'
                        ? JSON.stringify(lastResult.result, null, 2)
                        : String(lastResult.result)}
                    </pre>
                  )}
                </div>
                {lastResult.duration && (
                  <p className="text-xs text-muted-foreground">
                    Completed in {lastResult.duration}ms
                  </p>
                )}
              </div>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}

