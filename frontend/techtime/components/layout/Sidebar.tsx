'use client'

import { useState, useMemo } from 'react'
import { cn, formatDate, truncate } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from '@/components/ui/tooltip'
import {
  Plus,
  Search,
  PanelLeftClose,
  PanelLeft,
  MessageSquare,
  CheckCircle,
  AlertCircle,
  Clock,
  XCircle
} from 'lucide-react'
import type { SessionOutcome, SidebarProps } from '@/types'

const outcomeBadgeStyles: Record<SessionOutcome, string> = {
  resolved: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
  unresolved: 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/20',
  abandoned: 'bg-gray-500/15 text-gray-600 dark:text-gray-400 border-gray-500/20',
  in_progress: 'bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/20'
}

const outcomeIcons: Record<SessionOutcome, typeof CheckCircle> = {
  resolved: CheckCircle,
  unresolved: AlertCircle,
  abandoned: XCircle,
  in_progress: Clock
}

interface ExtendedSidebarProps extends SidebarProps {
  isCollapsed?: boolean
  onToggleCollapse?: () => void
}

export function Sidebar({
  sessions,
  activeSessionId,
  onSessionSelect,
  onNewSession,
  isLoading = false,
  isCollapsed = false,
  onToggleCollapse,
  className
}: ExtendedSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('')

  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessions
    const query = searchQuery.toLowerCase()
    return sessions.filter(s =>
      s.preview.toLowerCase().includes(query)
    )
  }, [sessions, searchQuery])

  return (
    <aside
      className={cn(
        'border-r bg-gradient-to-b from-background to-muted/30 flex flex-col h-full transition-all duration-300 ease-in-out',
        isCollapsed ? 'w-16' : 'w-72',
        className
      )}
    >
      {/* Header */}
      <div className={cn(
        'border-b bg-background/50 backdrop-blur-sm',
        isCollapsed ? 'p-2' : 'p-4'
      )}>
        <div className={cn(
          'flex items-center gap-2',
          isCollapsed ? 'flex-col' : 'justify-between mb-3'
        )}>
          {!isCollapsed && (
            <h2 className="font-semibold text-sm tracking-tight">Sessions</h2>
          )}
          {onToggleCollapse && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onToggleCollapse}
                  className="h-8 w-8 shrink-0"
                >
                  {isCollapsed ? (
                    <PanelLeft className="h-4 w-4" />
                  ) : (
                    <PanelLeftClose className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">
                {isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              </TooltipContent>
            </Tooltip>
          )}
        </div>

        {/* New Chat Button */}
        {isCollapsed ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                onClick={onNewSession}
                size="icon"
                className="w-full h-10 bg-primary hover:bg-primary/90 shadow-md"
              >
                <Plus className="h-5 w-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">New Chat</TooltipContent>
          </Tooltip>
        ) : (
          <Button
            onClick={onNewSession}
            className="w-full bg-primary hover:bg-primary/90 shadow-md font-medium"
          >
            <Plus className="h-4 w-4 mr-2" />
            New Chat
          </Button>
        )}

        {/* Search - only when expanded */}
        {!isCollapsed && (
          <div className="relative mt-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search sessions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 bg-muted/50 border-muted-foreground/20 focus:bg-background"
            />
          </div>
        )}
      </div>

      {/* Session List */}
      <ScrollArea className="flex-1">
        <div className={cn('py-2', isCollapsed ? 'px-2' : 'px-3')}>
          {isLoading ? (
            // Loading skeletons
            Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className={cn(
                'mb-2',
                isCollapsed ? 'p-2' : 'p-3'
              )}>
                {isCollapsed ? (
                  <Skeleton className="h-10 w-10 rounded-lg" />
                ) : (
                  <>
                    <Skeleton className="h-4 w-3/4 mb-2" />
                    <Skeleton className="h-3 w-1/2" />
                  </>
                )}
              </div>
            ))
          ) : filteredSessions.length === 0 ? (
            // Empty state
            <div className={cn(
              'text-center text-muted-foreground',
              isCollapsed ? 'p-2' : 'p-4'
            )}>
              {isCollapsed ? (
                <MessageSquare className="h-5 w-5 mx-auto opacity-50" />
              ) : (
                <div className="space-y-2">
                  <MessageSquare className="h-8 w-8 mx-auto opacity-50" />
                  <p className="text-sm">
                    {searchQuery ? 'No sessions match your search' : 'No sessions yet'}
                  </p>
                  <p className="text-xs opacity-75">
                    Start a new chat to begin troubleshooting
                  </p>
                </div>
              )}
            </div>
          ) : (
            // Session items
            filteredSessions.map(session => {
              const OutcomeIcon = outcomeIcons[session.outcome]
              const isActive = activeSessionId === session.id

              if (isCollapsed) {
                return (
                  <Tooltip key={session.id}>
                    <TooltipTrigger asChild>
                      <button
                        onClick={() => onSessionSelect(session.id)}
                        className={cn(
                          'w-full p-2 rounded-lg transition-all duration-200 mb-1',
                          'hover:bg-muted hover:scale-105',
                          'border-2',
                          isActive
                            ? 'bg-primary/10 border-primary shadow-sm'
                            : 'border-transparent'
                        )}
                      >
                        <OutcomeIcon className={cn(
                          'h-5 w-5 mx-auto',
                          session.outcome === 'resolved' && 'text-emerald-500',
                          session.outcome === 'unresolved' && 'text-amber-500',
                          session.outcome === 'abandoned' && 'text-gray-500',
                          session.outcome === 'in_progress' && 'text-blue-500'
                        )} />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="right" className="max-w-[200px]">
                      <p className="font-medium">{truncate(session.preview, 40)}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {formatDate(session.startTime, 'relative')}
                      </p>
                    </TooltipContent>
                  </Tooltip>
                )
              }

              return (
                <button
                  key={session.id}
                  onClick={() => onSessionSelect(session.id)}
                  className={cn(
                    'w-full text-left p-3 rounded-xl transition-all duration-200 mb-1',
                    'hover:bg-muted/80 hover:shadow-sm',
                    'border-2 group',
                    isActive
                      ? 'bg-primary/10 border-primary/50 shadow-sm'
                      : 'border-transparent hover:border-muted-foreground/10'
                  )}
                >
                  <div className="flex items-start gap-3">
                    <div className={cn(
                      'shrink-0 p-1.5 rounded-lg',
                      session.outcome === 'resolved' && 'bg-emerald-500/10',
                      session.outcome === 'unresolved' && 'bg-amber-500/10',
                      session.outcome === 'abandoned' && 'bg-gray-500/10',
                      session.outcome === 'in_progress' && 'bg-blue-500/10'
                    )}>
                      <OutcomeIcon className={cn(
                        'h-4 w-4',
                        session.outcome === 'resolved' && 'text-emerald-500',
                        session.outcome === 'unresolved' && 'text-amber-500',
                        session.outcome === 'abandoned' && 'text-gray-500',
                        session.outcome === 'in_progress' && 'text-blue-500'
                      )} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate group-hover:text-primary transition-colors">
                        {truncate(session.preview, 35)}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-muted-foreground">
                          {formatDate(session.startTime, 'relative')}
                        </span>
                        {session.issueCategory && (
                          <>
                            <span className="text-muted-foreground/30">•</span>
                            <Badge
                              variant="outline"
                              className="text-[10px] px-1.5 py-0 h-4 font-normal"
                            >
                              {session.issueCategory}
                            </Badge>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              )
            })
          )}
        </div>
      </ScrollArea>

      {/* Footer - Session count */}
      {!isCollapsed && sessions.length > 0 && (
        <div className="p-3 border-t bg-muted/30 text-center">
          <p className="text-xs text-muted-foreground">
            {filteredSessions.length} of {sessions.length} session{sessions.length !== 1 ? 's' : ''}
          </p>
        </div>
      )}
    </aside>
  )
}
