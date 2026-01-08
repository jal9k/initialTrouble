'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { useChat } from '@/hooks/use-chat'
import { useOSILadder } from '@/hooks/use-osi-ladder'
import { useManualToolPanel } from '@/hooks/use-manual-tool-panel'
import { Sidebar } from '@/components/layout/Sidebar'
import { MobileSidebar } from '@/components/layout/MobileSidebar'
import { RightPanel } from '@/components/layout/RightPanel'
import { ChatWindow } from '@/components/chat/ChatWindow'
import { listSessions, deleteSession, updateSession } from '@/lib/api'
import type { SessionListItem, DiagnosticTool } from '@/types'

interface ChatPageClientProps {
  initialSessions: SessionListItem[]
  tools: DiagnosticTool[]
}

export function ChatPageClient({
  initialSessions,
  tools
}: ChatPageClientProps) {
  const [sessions, setSessions] = useState(initialSessions)
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(false)
  // Key to force ChatWindow remount on new conversation
  const [chatKey, setChatKey] = useState(0)
  
  // Track if this is the first message in a session (for updating preview)
  const isFirstMessageRef = useRef(true)

  // Function to refetch sessions from the API
  const refetchSessions = useCallback(async () => {
    try {
      const result = await listSessions({ pageSize: 20 })
      // Merge backend data with local data, preserving local previews for recent sessions
      // that might not have synced to the backend yet
      setSessions(prev => {
        const backendMap = new Map(result.items.map(s => [s.id, s]))
        const localOnlyIds = new Set<string>()
        
        // Find sessions that exist locally but not in backend (newly created)
        prev.forEach(s => {
          if (!backendMap.has(s.id)) {
            localOnlyIds.add(s.id)
          }
        })
        
        // Merge: use backend data but preserve local preview if backend still has placeholder
        const merged = result.items.map(backendSession => {
          const localSession = prev.find(s => s.id === backendSession.id)
          // If local session has a real preview and backend still has placeholder, keep local
          if (localSession && 
              localSession.preview !== 'New conversation...' && 
              backendSession.preview === 'New conversation...') {
            return { ...backendSession, preview: localSession.preview }
          }
          return backendSession
        })
        
        // Add any local-only sessions to the front (they haven't synced yet)
        const localOnly = prev.filter(s => localOnlyIds.has(s.id))
        return [...localOnly, ...merged]
      })
    } catch (error) {
      console.error('Failed to refetch sessions:', error)
    }
  }, [])

  // Callback when a new session starts (used by ChatWindow's internal useChat)
  const handleSessionStart = useCallback((id: string) => {
    setActiveSessionId(id)
    isFirstMessageRef.current = true
    // Add to sessions list with placeholder preview
    setSessions(prev => {
      // Check if session already exists (e.g., from initial load)
      if (prev.some(s => s.id === id)) {
        return prev
      }
      return [{
        id,
        startTime: new Date(),
        outcome: 'in_progress',
        preview: 'New conversation...'
      }, ...prev]
    })
  }, [])

  // Callback when a message is sent/received - update session preview
  const handleMessage = useCallback((message: { role: string; content: string }) => {
    if (message.role === 'user' && activeSessionId) {
      const preview = message.content.slice(0, 50) + (message.content.length > 50 ? '...' : '')
      
      // Update the active session's preview with the user's message
      setSessions(prev => prev.map(session => 
        session.id === activeSessionId
          ? { ...session, preview }
          : session
      ))
      
      // If this is the first message, refetch after a delay to get the updated data from backend
      if (isFirstMessageRef.current) {
        isFirstMessageRef.current = false
        // Refetch after a short delay to allow backend to process
        setTimeout(refetchSessions, 1000)
      }
    }
  }, [activeSessionId, refetchSessions])

  // Chat state (for loading conversations from sidebar)
  const chat = useChat({
    onSessionStart: handleSessionStart
  })

  // OSI ladder state
  const osiLadder = useOSILadder({
    onLayerChange: (layer, status) => {
      console.log(`Layer ${layer} is now ${status}`)
    }
  })

  // Manual tool panel state
  const toolPanel = useManualToolPanel({
    tools,
    onExecutionComplete: (result) => {
      // Update OSI ladder based on tool result
      const tool = tools.find(t => t.name === result.name)
      if (tool) {
        if (result.error) {
          osiLadder.failLayer(tool.osiLayer, result.error)
        } else {
          osiLadder.passLayer(tool.osiLayer, JSON.stringify(result.result))
        }
      }
    }
  })

  const handleSessionSelect = useCallback((sessionId: string) => {
    setActiveSessionId(sessionId)
    // Increment chatKey to force ChatWindow remount with the new session
    // ChatWindow's useChat will auto-load messages via initialConversationId
    setChatKey(k => k + 1)
  }, [])

  const handleNewSession = useCallback(() => {
    chat.startNewConversation()
    osiLadder.reset()
    toolPanel.clearAllResults()
    setActiveSessionId(null)
    isFirstMessageRef.current = true
    // Increment key to force ChatWindow remount with fresh state
    setChatKey(k => k + 1)
  }, [chat, osiLadder, toolPanel])

  // Session action handlers
  const handleDeleteSession = useCallback(async (sessionId: string) => {
    try {
      // Call API to delete session from backend
      await deleteSession(sessionId)
      
      // Remove session from local state
      setSessions(prev => prev.filter(s => s.id !== sessionId))
      
      // If deleted session was active, clear it
      if (activeSessionId === sessionId) {
        setActiveSessionId(null)
        setChatKey(k => k + 1)
      }
    } catch (error) {
      console.error('Failed to delete session:', error)
      // Optionally show error to user
    }
  }, [activeSessionId])

  const handleRenameSession = useCallback(async (sessionId: string) => {
    const newName = prompt('Enter new name for session:')
    if (!newName) return
    
    try {
      // Call API to update session preview
      await updateSession(sessionId, { preview: newName })
      
      // Update local state
      setSessions(prev => prev.map(s => 
        s.id === sessionId ? { ...s, preview: newName } : s
      ))
    } catch (error) {
      console.error('Failed to rename session:', error)
    }
  }, [])

  const handleArchiveSession = useCallback(async (sessionId: string) => {
    try {
      // Call API to archive session (set outcome to 'abandoned')
      await updateSession(sessionId, { outcome: 'abandoned' })
      
      // Remove from the visible list (archived sessions won't show by default)
      setSessions(prev => prev.filter(s => s.id !== sessionId))
      
      // If archived session was active, clear it
      if (activeSessionId === sessionId) {
        setActiveSessionId(null)
        setChatKey(k => k + 1)
      }
    } catch (error) {
      console.error('Failed to archive session:', error)
    }
  }, [activeSessionId])
  
  // Reset first message flag when session changes
  useEffect(() => {
    isFirstMessageRef.current = true
  }, [activeSessionId])

  const handleToggleSidebar = useCallback(() => {
    setSidebarCollapsed(prev => !prev)
  }, [])

  const handleToggleRightPanel = useCallback(() => {
    setRightPanelCollapsed(prev => !prev)
  }, [])

  return (
    <div className="h-[calc(100vh-56px)]">
      {/* Mobile sidebar trigger */}
      <div className="md:hidden p-2 border-b flex items-center gap-2">
        <MobileSidebar
          sessions={sessions}
          activeSessionId={activeSessionId || undefined}
          onSessionSelect={handleSessionSelect}
          onNewSession={handleNewSession}
        />
        <span className="text-sm font-medium">TechTim(e)</span>
      </div>

      <div className="hidden md:flex h-full">
        {/* Left Sidebar - Desktop only */}
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId || undefined}
          onSessionSelect={handleSessionSelect}
          onNewSession={handleNewSession}
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={handleToggleSidebar}
          onDeleteSession={handleDeleteSession}
          onRenameSession={handleRenameSession}
          onArchiveSession={handleArchiveSession}
        />

        {/* Main Chat Window */}
        <div className="flex-1 min-w-0">
          <ChatWindow
            key={chatKey}
            initialConversationId={activeSessionId || undefined}
            onSessionStart={handleSessionStart}
            onMessage={handleMessage}
          />
        </div>

        {/* Right Panel - Diagnostics & Tools */}
        <RightPanel
          layers={osiLadder.layers}
          currentLayer={osiLadder.currentLayer || undefined}
          tools={tools}
          onExecute={toolPanel.executeTool}
          results={toolPanel.results}
          executingTool={toolPanel.executingTool}
          onClearAll={toolPanel.clearAllResults}
          isCollapsed={rightPanelCollapsed}
          onToggleCollapse={handleToggleRightPanel}
          className="hidden lg:flex"
        />
      </div>

      {/* Mobile view - just ChatWindow */}
      <div className="md:hidden h-full">
        <ChatWindow
          key={`mobile-${chatKey}`}
          initialConversationId={activeSessionId || undefined}
          onSessionStart={handleSessionStart}
          onMessage={handleMessage}
        />
      </div>
    </div>
  )
}
