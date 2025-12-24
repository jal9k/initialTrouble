Next.js Frontend for TechTime
Overview
Build a modern Next.js frontend with two main sections: an AI-powered chat interface for L1 desktop support, and an analytics dashboard for monitoring sessions and tool performance.

Architecture
Python Backend - Port 8000
Next.js Frontend - Port 3000
App Router Pages
Key Components
FastAPI
/ws
/chat, /health
WebSocket Client
API Client
ChatWindow
OSILadderViz
ManualToolPanel
Analytics Charts
/chat - Chat Interface
/dashboard - Analytics
/history - Session History


Tech Stack
Framework: Next.js 15 (App Router)
Styling: Tailwind CSS + shadcn/ui components
State: React hooks + URL state (nuqs for search params)
Real-time: Native WebSocket for chat streaming
Charts: Recharts for analytics visualizations
Page Structure
1. Chat Interface (/chat)
Main troubleshooting page with three-column layout:| Left Sidebar | Center | Right Sidebar |

|--------------|--------|---------------|

| Session History | Chat Messages | OSI Ladder Viz |

| New Chat Button | Input Area | Manual Tool Panel |Key Features:

Real-time WebSocket connection for streaming responses
Tool execution indicators (spinner + name when tool runs)
Markdown rendering for AI responses
Session persistence in localStorage + backend
2. Analytics Dashboard (/dashboard)
Grid layout with metric cards and charts:

Summary Cards: Total sessions, resolution rate, avg time to resolution, total cost
Charts: Sessions over time, issue category breakdown, tool usage frequency
Tables: Recent sessions list, tool performance stats
3. Session History (/history)
Paginated list of past sessions with:

Outcome badges (resolved/unresolved/abandoned)
Issue category tags
Click to replay/continue conversation
Key Components
ChatWindow
Message list with user/assistant/tool-result styling
Auto-scroll to bottom on new messages
Loading state with typing indicator
OSILadderViz
Vertical ladder showing 5 diagnostic layers
Highlights current layer being tested
Green/red/gray states for pass/fail/pending
Updates in real-time as tools execute
ManualToolPanel
Collapsible accordion for each diagnostic tool
Parameter inputs where applicable
"Run" button to execute tool directly
Shows raw result in expandable panel
AnalyticsCharts
SessionsOverTime (line chart)
IssueCategoryPie (pie chart)
ToolUsageBar (horizontal bar chart)
ResolutionFunnel (funnel showing session outcomes)
API Integration
New Backend Endpoints Needed
The current backend needs a few additional endpoints for the dashboard:

# Add to backend/main.py
GET /api/sessions - List sessions with filters
GET /api/sessions/{id} - Get session details
GET /api/analytics/summary - Get SessionSummary
GET /api/analytics/tools - Get ToolStats list
GET /api/tools - List available diagnostic tools
POST /api/tools/{name}/execute - Execute tool directly


WebSocket Message Format
// Client -> Server
{ message: string, conversation_id?: string }

// Server -> Client (already implemented)
{ response: string, tool_calls: ToolCall[] | null, conversation_id: string }


File Structure
frontend/
  app/
    layout.tsx              # Root layout with nav
    page.tsx                # Redirect to /chat
    chat/
      page.tsx              # Chat interface
    dashboard/
      page.tsx              # Analytics dashboard
    history/
      page.tsx              # Session history
    api/                    # API route handlers (proxy if needed)
  components/
    ui/                     # shadcn components
    chat/
      ChatWindow.tsx
      MessageBubble.tsx
      ToolExecutionCard.tsx
    diagnostics/
      OSILadderViz.tsx
      ManualToolPanel.tsx
      ToolCard.tsx
    analytics/
      SummaryCards.tsx
      SessionsChart.tsx
      ToolStatsTable.tsx
    layout/
      Header.tsx
      Sidebar.tsx
  lib/
    api.ts                  # REST API client
    websocket.ts            # WebSocket client hook
    utils.ts                # Utilities
  hooks/
    use-chat.ts             # Chat state management
    use-websocket.ts        # WebSocket connection
  types/
    index.ts                # TypeScript interfaces
  styles/
    globals.css             # Tailwind + custom styles


Design Direction
Theme: npx shadcn@latest add https://tweakcn.com/r/themes/claude.json

Implementation Order
Project Setup - Initialize Next.js, Tailwind, shadcn/ui
Backend API Extensions - Add missing endpoints for analytics/tools
Core Layout - Header, navigation, page shells
Chat Interface - WebSocket connection, message rendering, input
OSI Ladder Visualization - Real-time diagnostic progress display
Manual Tool Panel - Direct tool execution UI
Session History - List, load, continue past conversations
Analytics Dashboard - Summary cards and charts