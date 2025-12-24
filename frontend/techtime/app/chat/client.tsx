'use client'

import { useState, useCallback } from 'react'
import { useChat } from '@/hooks/use-chat'
import { useOSILadder } from '@/hooks/use-osi-ladder'
import { useManualToolPanel } from '@/hooks/use-manual-tool-panel'
import { Sidebar } from '@/components/layout/Sidebar'
import { MobileSidebar } from '@/components/layout/MobileSidebar'
import { RightPanel } from '@/components/layout/RightPanel'
import { ChatWindow } from '@/components/chat/ChatWindow'
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

  // Callback when a new session starts (used by ChatWindow's internal useChat)
  const handleSessionStart = useCallback((id: string) => {
    setActiveSessionId(id)
    // Add to sessions list
    setSessions(prev => [{
      id,
      startTime: new Date(),
      outcome: 'in_progress',
      preview: 'New conversation...'
    }, ...prev])
  }, [])

  // Callback when a message is sent/received - update session preview
  const handleMessage = useCallback((message: { role: string; content: string }) => {
    if (message.role === 'user') {
      // Update the active session's preview with the user's message
      setSessions(prev => prev.map(session => 
        session.id === activeSessionId
          ? { ...session, preview: message.content.slice(0, 50) + (message.content.length > 50 ? '...' : '') }
          : session
      ))
    }
  }, [activeSessionId])

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
    chat.loadConversation(sessionId)
  }, [chat])

  const handleNewSession = useCallback(() => {
    chat.startNewConversation()
    osiLadder.reset()
    toolPanel.clearAllResults()
    setActiveSessionId(null)
    // Increment key to force ChatWindow remount with fresh state
    setChatKey(k => k + 1)
  }, [chat, osiLadder, toolPanel])

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
