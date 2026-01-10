# TechTim(e) - Application Architecture Summary

> An intelligent, cross-platform L1 desktop support tool that uses LLM reasoning (Ollama/OpenAI) to diagnose and troubleshoot IT issues.

---

## Table of Contents

1. [High-Level Overview](#high-level-overview)
2. [System Architecture](#system-architecture)
3. [Backend Architecture](#backend-architecture)
4. [Frontend Architecture](#frontend-architecture)
5. [Data Flow](#data-flow)
6. [Analytics System](#analytics-system)
7. [LLM Integration](#llm-integration)
8. [Tool/Diagnostic System](#tooldiagnostic-system)
9. [Infrastructure & Deployment](#infrastructure--deployment)
10. [File Dependency Map](#file-dependency-map)

---

## High-Level Overview

TechTim(e) is a full-stack AI-powered IT support assistant that:
- **Diagnoses** network and system issues using structured OSI-layer troubleshooting
- **Executes** diagnostic tools automatically based on LLM reasoning
- **Tracks** sessions, tool usage, and resolution rates via analytics
- **Supports** both CLI and Web interfaces

```
┌──────────────────────────────────────────────────────────────────┐
│                         TechTim(e)                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐      ┌─────────────┐      ┌──────────────┐    │
│   │   Web UI    │      │     CLI     │      │  API Clients │    │
│   │  (Next.js)  │      │   (Typer)   │      │   (REST/WS)  │    │
│   └──────┬──────┘      └──────┬──────┘      └──────┬───────┘    │
│          │                    │                    │             │
│          └────────────────────┼────────────────────┘             │
│                               ▼                                  │
│                    ┌──────────────────┐                          │
│                    │   FastAPI Server │                          │
│                    │   (REST + WS)    │                          │
│                    └────────┬─────────┘                          │
│                             │                                    │
│          ┌──────────────────┼──────────────────┐                 │
│          ▼                  ▼                  ▼                 │
│   ┌──────────────┐  ┌──────────────┐  ┌───────────────┐         │
│   │  LLM Router  │  │Tool Registry │  │  Analytics    │         │
│   │ (Ollama/GPT) │  │ (Diagnostics)│  │  (SQLite)     │         │
│   └──────────────┘  └──────────────┘  └───────────────┘         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## System Architecture

### Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Next.js)                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                                                                         │ │
│ │   app/                    components/               hooks/              │ │
│ │   ├── layout.tsx ───────► Header.tsx               ├── use-chat.ts     │ │
│ │   ├── page.tsx            Sidebar.tsx              ├── use-websocket.ts│ │
│ │   └── chat/               ChatWindow.tsx           └── use-osi-ladder  │ │
│ │       ├── page.tsx        MessageBubble.tsx                            │ │
│ │       └── client.tsx      ToolExecutionCard.tsx                        │ │
│ │                                │                                       │ │
│ │   lib/                         │                                       │ │
│ │   ├── api.ts ◄─────────────────┤ (fetch/REST)                          │ │
│ │   └── websocket.ts ◄───────────┘ (WS connection)                       │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                               │  HTTP/WS                                    │
└───────────────────────────────┼─────────────────────────────────────────────┘
                                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (Python/FastAPI)                         │
│ ┌───────────────────────────────────────────────────────────────────────────┐ │
│ │                                                                           │ │
│ │   main.py (FastAPI App)                                                   │ │
│ │   ├── /health             → Health check endpoint                         │ │
│ │   ├── /chat (POST)        → Chat completion with tools                    │ │
│ │   ├── /ws                 → WebSocket for real-time chat                  │ │
│ │   ├── /api/sessions       → Session list/CRUD                             │ │
│ │   └── /api/tools          → Tool listing/execution                        │ │
│ │            │                                                              │ │
│ │            ▼                                                              │ │
│ │   ┌────────────────┐    ┌─────────────────┐    ┌───────────────────┐     │ │
│ │   │   LLM Router   │    │  Tool Registry  │    │ Analytics Module  │     │ │
│ │   │ (router.py)    │    │ (registry.py)   │    │ (collector.py)    │     │ │
│ │   └───────┬────────┘    └────────┬────────┘    └─────────┬─────────┘     │ │
│ │           │                      │                       │               │ │
│ │           ▼                      ▼                       ▼               │ │
│ │   ┌──────────────┐      ┌──────────────┐        ┌───────────────┐       │ │
│ │   │ LLM Clients  │      │ Diagnostic   │        │   SQLite DB   │       │ │
│ │   │ ├─ Ollama    │      │ Functions    │        │ analytics.db  │       │ │
│ │   │ └─ OpenAI    │      │ (20+ tools)  │        └───────────────┘       │ │
│ │   └──────────────┘      └──────────────┘                                 │ │
│ │                                                                           │ │
│ └───────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Backend Architecture

### Directory Structure

```
backend/
├── __init__.py           # Package init, version
├── main.py               # FastAPI app, routes, WebSocket
├── config.py             # Pydantic settings from .env
├── cli.py                # Typer CLI interface
├── prompts.py            # Agent prompt loader
├── logging_config.py     # Logging setup
│
├── llm/                  # LLM Integration Layer
│   ├── __init__.py       # Exports ChatMessage, LLMRouter
│   ├── base.py           # BaseLLMClient abstract class
│   ├── router.py         # Multi-backend router with fallback
│   ├── ollama_client.py  # Ollama API client
│   └── openai_client.py  # OpenAI API client
│
├── tools/                # Tool Registry System
│   ├── __init__.py       # Exports ToolRegistry, get_registry
│   ├── registry.py       # Tool registration & execution
│   ├── schemas.py        # ToolDefinition, ToolCall, ToolResult
│   └── api.py            # REST API for tools
│
├── diagnostics/          # Diagnostic Tool Implementations
│   ├── __init__.py       # Tool registration function
│   ├── base.py           # BaseDiagnostic, DiagnosticResult
│   ├── platform.py       # Platform detection, command executor
│   ├── adapter.py        # check_adapter_status
│   ├── ip_config.py      # get_ip_config
│   ├── connectivity.py   # ping_gateway, ping_dns
│   ├── dns.py            # test_dns_resolution
│   ├── wifi.py           # enable_wifi
│   ├── bluetooth.py      # toggle_bluetooth
│   ├── vpn.py            # test_vpn_connectivity
│   ├── process_mgmt.py   # kill_process
│   ├── temp_files.py     # cleanup_temp_files
│   ├── reachability.py   # ping_address, traceroute
│   ├── ip_reset.py       # ip_release, ip_renew, flush_dns
│   └── windows/          # Windows-specific tools
│       ├── dell_audio.py
│       ├── office_repair.py
│       ├── system_repair.py
│       ├── log_analysis.py
│       └── robocopy.py
│
└── agents/               # Multi-OS Agent System (experimental)
    ├── base.py
    ├── manager.py
    ├── macos.py
    ├── windows.py
    └── linux.py
```

### Key Backend Files Explained

#### `main.py` - FastAPI Application Entry Point

```python
# Creates FastAPI app with:
# - CORS middleware for frontend
# - Lifespan manager for startup/shutdown
# - Routes: /health, /chat, /ws, /api/sessions, /api/tools
# - Manages AppState (LLM router, tool registry, analytics)
```

**Key Responsibilities:**
- Initializes all subsystems on startup
- Routes HTTP/WebSocket requests
- Orchestrates multi-turn tool execution loop
- Persists messages to analytics database

#### `config.py` - Configuration Management

```python
class Settings(BaseSettings):
    llm_backend: Literal["ollama", "openai"]
    ollama_host: str
    ollama_model: str
    openai_api_key: str
    openai_model: str
    # ... server, diagnostic settings
```

**Loads from:** `.env` file via Pydantic Settings

#### `llm/router.py` - LLM Backend Router

```
┌────────────────────────────────────────────┐
│              LLMRouter                     │
├────────────────────────────────────────────┤
│  preferred_backend: "ollama" | "openai"    │
│                                            │
│  ┌─────────────┐    ┌─────────────┐       │
│  │ OllamaClient│    │OpenAI Client│       │
│  │  (primary)  │ ◄──│  (fallback) │       │
│  └─────────────┘    └─────────────┘       │
│                                            │
│  get_client() → tries preferred first,     │
│                 falls back if unavailable  │
│  chat() → routes to active client          │
└────────────────────────────────────────────┘
```

**Features:**
- Automatic fallback between backends
- Analytics integration for tracking
- Token usage tracking

#### `tools/registry.py` - Tool Registration System

```python
# Global singleton pattern
_registry: ToolRegistry | None = None

def get_registry() -> ToolRegistry:
    """Get or create global tool registry."""

# Decorator for tool registration
@tool(name="ping_gateway", description="...", parameters=[...])
async def ping_gateway(gateway: str = None):
    ...
```

**Key Methods:**
- `register()` - Decorator for tool registration
- `execute()` - Execute a tool call from LLM
- `get_all_definitions()` - Get OpenAI-format tool schemas

#### `diagnostics/__init__.py` - Tool Registration Hub

Registers all 20+ diagnostic tools with detailed descriptions optimized for small LLMs:

```
┌─────────────────────────────────────────────────────────────────┐
│                    DIAGNOSTIC TOOLS                             │
├─────────────────────────────────────────────────────────────────┤
│ OSI Layer 1-2 (Physical/Link)                                   │
│   • check_adapter_status - Network adapter status               │
│   • enable_wifi - Enable WiFi adapter                           │
│   • toggle_bluetooth - Bluetooth control                        │
├─────────────────────────────────────────────────────────────────┤
│ OSI Layer 3 (Network)                                           │
│   • get_ip_config - IP/subnet/gateway info                      │
│   • ping_gateway - Test router connectivity                     │
│   • ping_dns - Test external DNS servers                        │
│   • ping_address - Ping arbitrary host                          │
│   • traceroute - Network path tracing                           │
│   • ip_release/ip_renew - DHCP operations                       │
├─────────────────────────────────────────────────────────────────┤
│ OSI Layer 7 (Application)                                       │
│   • test_dns_resolution - DNS lookup test                       │
│   • flush_dns - Clear DNS cache                                 │
│   • test_vpn_connectivity - VPN status                          │
├─────────────────────────────────────────────────────────────────┤
│ System Maintenance                                              │
│   • cleanup_temp_files - Disk cleanup                           │
│   • kill_process - Process management                           │
├─────────────────────────────────────────────────────────────────┤
│ Windows-Only                                                    │
│   • fix_dell_audio - Dell audio driver fix                      │
│   • repair_office365 - Office repair                            │
│   • run_dism_sfc - System file repair                           │
│   • review_system_logs - Event log analysis                     │
│   • robocopy - Robust file copy                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture

### Directory Structure

```
frontend/techtime/
├── app/                          # Next.js App Router
│   ├── layout.tsx                # Root layout (theme, header)
│   ├── page.tsx                  # Landing page
│   ├── chat/
│   │   ├── page.tsx              # Chat page (server component)
│   │   └── client.tsx            # Chat page client component
│   ├── dashboard/
│   │   └── page.tsx              # Analytics dashboard
│   └── history/
│       └── page.tsx              # Session history
│
├── components/
│   ├── layout/
│   │   ├── Header.tsx            # App header with nav
│   │   └── Sidebar.tsx           # Session list sidebar
│   ├── chat/
│   │   ├── ChatWindow.tsx        # Main chat interface
│   │   ├── MessageBubble.tsx     # Message rendering
│   │   └── ToolExecutionCard.tsx # Tool execution display
│   ├── diagnostics/
│   │   ├── OSILadderViz.tsx      # OSI layer visualization
│   │   ├── ManualToolPanel.tsx   # Manual tool execution
│   │   └── ToolCard.tsx          # Individual tool card
│   ├── analytics/
│   │   ├── SummaryCards.tsx      # Summary statistics
│   │   ├── SessionsChart.tsx     # Time series chart
│   │   └── ToolStatsTable.tsx    # Tool usage table
│   └── ui/                       # shadcn/ui components
│       ├── button.tsx
│       ├── card.tsx
│       ├── scroll-area.tsx
│       └── ... (26 components)
│
├── hooks/
│   ├── use-chat.ts               # Chat state management
│   ├── use-websocket.ts          # WebSocket connection
│   ├── use-osi-ladder.ts         # OSI layer state
│   └── use-tool-execution.ts     # Tool execution state
│
├── lib/
│   ├── api.ts                    # REST API client
│   ├── websocket.ts              # WebSocket client class
│   └── utils.ts                  # Utility functions
│
├── types/
│   └── index.ts                  # TypeScript interfaces
│
└── globals.css                   # Tailwind + custom styles
```

### Key Frontend Files Explained

#### `app/layout.tsx` - Root Layout

```tsx
// Wraps entire app with:
// - ThemeProvider (dark/light mode)
// - TooltipProvider (UI tooltips)
// - Header component
// - Inter font from Google Fonts
```

#### `hooks/use-chat.ts` - Chat State Management

```
┌────────────────────────────────────────────────────────────┐
│                     useChat Hook                           │
├────────────────────────────────────────────────────────────┤
│ State:                                                     │
│   messages: Message[]                                      │
│   conversationId: string | null                            │
│   isStreaming: boolean                                     │
│   currentToolExecution: ToolCall | null                    │
│   error: Error | null                                      │
├────────────────────────────────────────────────────────────┤
│ Actions:                                                   │
│   sendMessage(content) → sends via WebSocket               │
│   loadConversation(id) → fetches from API                  │
│   clearMessages() → resets state                           │
│   retryLastMessage() → resends failed message              │
├────────────────────────────────────────────────────────────┤
│ Integrates with:                                           │
│   useWebSocket → real-time communication                   │
│   localStorage → message persistence                       │
│   API → session loading                                    │
└────────────────────────────────────────────────────────────┘
```

#### `lib/websocket.ts` - WebSocket Client

```typescript
class ChatWebSocket {
  // Connection management
  connect() / disconnect()
  
  // Reconnection with exponential backoff
  handleReconnect()
  
  // Message queue for offline sends
  messageQueue: ClientMessage[]
  
  // Event callbacks
  onMessage, onOpen, onClose, onError
}

// Singleton pattern
getWebSocket() → returns global instance
```

#### `lib/api.ts` - REST API Client

Provides typed functions for all API endpoints:

```typescript
// Health
getHealth(): Promise<HealthResponse>

// Sessions
listSessions(params): Promise<PaginatedResponse<SessionListItem>>
getSessionMessages(id): Promise<Message[]>
deleteSession(id): Promise<{success: boolean}>
updateSession(id, params): Promise<UpdateSessionResponse>

// Analytics
getAnalyticsSummary(): Promise<SessionSummary>
getToolStats(): Promise<ToolStats[]>

// Tools
listTools(): Promise<DiagnosticTool[]>
executeTool(params): Promise<ToolResult>
```

#### `types/index.ts` - TypeScript Definitions

```typescript
// Core message types
interface Message {
  id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  timestamp: Date
  toolCalls?: ToolCall[]
  diagnostics?: ResponseDiagnostics
}

// Session types
type SessionOutcome = 'resolved' | 'unresolved' | 'abandoned' | 'in_progress'

// OSI Layer visualization
interface LayerState {
  layer: OSILayer
  status: 'pending' | 'testing' | 'pass' | 'fail' | 'skipped'
}

// WebSocket message formats
interface ClientMessage { message: string; conversation_id?: string }
interface ServerMessage { response: string; tool_calls: ToolCall[] | null; ... }
```

---

## Data Flow

### Chat Message Flow (WebSocket)

```
┌──────────┐                                           ┌───────────┐
│ Frontend │                                           │  Backend  │
└────┬─────┘                                           └─────┬─────┘
     │                                                       │
     │  1. User types message                                │
     │─────────────────────────────────────────────────────►│
     │     { message: "WiFi not working",                    │
     │       conversation_id: "abc123" }                     │
     │                                                       │
     │                          2. Backend processes:        │
     │                          ├─ Add to conversation       │
     │                          ├─ Send to LLM              │
     │                          ├─ LLM requests tool call   │
     │                          ├─ Execute tool             │
     │                          ├─ Return result to LLM     │
     │                          └─ Get final response       │
     │                                                       │
     │◄─────────────────────────────────────────────────────│
     │  3. Response with tool calls                          │
     │     { response: "I checked your adapter...",          │
     │       tool_calls: [{name: "check_adapter_status"}],   │
     │       diagnostics: {...} }                            │
     │                                                       │
     │  4. Frontend updates UI                               │
     │  ├─ Show assistant message                            │
     │  ├─ Display tool execution card                       │
     │  └─ Update OSI ladder visualization                   │
     ▼                                                       ▼
```

### Tool Execution Loop (Backend)

```
┌────────────────────────────────────────────────────────────────┐
│                    execute_tool_loop()                         │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│   for iteration in range(MAX_ITERATIONS):                      │
│       │                                                        │
│       ├─► [1] Send to LLM (tool_choice="required"/"auto")      │
│       │                                                        │
│       ├─► [2] Check if LLM returned tool calls                 │
│       │   └─► No → Return final response                       │
│       │                                                        │
│       ├─► [3] For each tool_call:                              │
│       │       ├─ Execute via tool_registry.execute()           │
│       │       ├─ Add result to messages                        │
│       │       └─ Track in analytics                            │
│       │                                                        │
│       └─► [4] Loop continues...                                │
│                                                                │
│   After loop: Return final message + action_tool_called flag   │
└────────────────────────────────────────────────────────────────┘
```

---

## Analytics System

### Architecture

```
analytics/
├── __init__.py          # Module exports
├── models.py            # Pydantic models for all entities
├── collector.py         # AnalyticsCollector class
├── storage.py           # SQLite storage backend
├── api.py               # REST API endpoints
├── cost.py              # OpenAI cost calculator
└── patterns.py          # Pattern analysis
```

### Database Schema

```sql
-- Sessions table
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    outcome TEXT DEFAULT 'in_progress',  -- resolved/unresolved/abandoned
    issue_category TEXT DEFAULT 'unknown',
    preview TEXT,
    message_count INTEGER,
    tool_call_count INTEGER,
    llm_backend TEXT,
    model_name TEXT,
    estimated_cost_usd REAL,
    total_prompt_tokens INTEGER,
    total_completion_tokens INTEGER
);

-- Tool events table
CREATE TABLE tool_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    execution_time_ms INTEGER,
    success INTEGER,
    error_message TEXT,
    arguments TEXT,  -- JSON
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Messages table (chat history)
CREATE TABLE messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    tool_call_id TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

### Analytics Flow

```
User Action → AnalyticsCollector → AnalyticsStorage → SQLite
                    │
                    ├── record_user_message()
                    ├── record_tool_call()
                    ├── record_llm_call()
                    └── end_session(outcome)
```

---

## LLM Integration

### Multi-Backend Support

```
┌─────────────────────────────────────────────────────────────┐
│                     LLM Router                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Configuration:                                             │
│  ├── llm_backend: "ollama" (default) or "openai"            │
│  ├── ollama_host: "http://localhost:11434"                  │
│  ├── ollama_model: "ministral-3:3b"                         │
│  └── openai_model: "gpt-4o-mini"                            │
│                                                             │
│  Fallback Logic:                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. Try preferred backend                            │   │
│  │ 2. If unavailable → try alternate backend           │   │
│  │ 3. Record fallback event in analytics               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Tool Calling:                                              │
│  ├── Converts tools to OpenAI function format              │
│  ├── Supports tool_choice: "auto"/"required"/"none"        │
│  └── Handles tool call responses and execution             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Prompt System

Located in `prompts/` directory:

```
prompts/
├── diagnostic_agent.md   # Main diagnostic prompt (OSI ladder)
├── triage_agent.md       # Quick issue categorization
├── remediation_agent.md  # Fix suggestions
├── quick_check_agent.md  # Fast health check
├── manager_agent.md      # Multi-OS coordinator
├── macos_agent.md        # macOS specialist
├── windows_agent.md      # Windows specialist
└── linux_agent.md        # Linux specialist
```

Key prompt features:
- **Decision boundaries** - Clear "CALL WHEN" / "DO NOT CALL" conditions
- **OSI ladder sequence** - Structured troubleshooting order
- **Automatic fix attempts** - Try enable_wifi before giving up
- **Verification** - Check fixes worked before concluding

---

## Tool/Diagnostic System

### Tool Definition Schema

```python
@dataclass
class ToolDefinition:
    name: str                    # e.g., "ping_gateway"
    description: str             # Detailed for LLM
    parameters: list[ToolParameter]
    
    def to_openai_schema(self) -> dict:
        """Convert to OpenAI function calling format."""
        
    def to_ollama_schema(self) -> dict:
        """Convert to Ollama tool format."""
```

### Tool Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Tool Execution                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. LLM returns ToolCall:                                       │
│     { "name": "ping_gateway",                                   │
│       "arguments": { "gateway": "192.168.1.1" } }               │
│                                                                 │
│  2. Registry normalizes arguments:                              │
│     - Maps aliases (gateway_ip → gateway)                       │
│     - Validates types                                           │
│                                                                 │
│  3. Execute diagnostic function:                                │
│     async def ping_gateway(gateway: str = None):                │
│         result = await executor.run_command(["ping", ...])      │
│         return DiagnosticResult(...)                            │
│                                                                 │
│  4. Return ToolResult:                                          │
│     { "success": true,                                          │
│       "content": "Gateway 192.168.1.1 is reachable..." }        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Cross-Platform Support

```python
class Platform(Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"

def get_platform() -> Platform:
    """Detect current platform."""

class CommandExecutor:
    """Cross-platform command execution."""
    
    async def run_command(
        self, 
        cmd: list[str], 
        timeout: int = 10
    ) -> tuple[str, str, int]:
        """Execute shell command with timeout."""
```

Each diagnostic tool uses platform-specific commands:

| Tool | Windows | macOS | Linux |
|------|---------|-------|-------|
| ping_gateway | `ping -n 4` | `ping -c 4` | `ping -c 4` |
| get_ip_config | `ipconfig /all` | `ifconfig` | `ip addr` |
| enable_wifi | `netsh interface set` | `networksetup -setairportpower` | `nmcli radio wifi on` |

---

## Infrastructure & Deployment

### Environment Configuration

```bash
# .env file
LLM_BACKEND=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=ministral-3:3b

OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

HOST=0.0.0.0
PORT=8000
DEBUG=false
```

### Running the Application

```bash
# Backend API Server
uvicorn backend.main:app --reload --port 8000

# CLI Interface
python -m backend.cli chat

# Frontend (Next.js)
cd frontend/techtime && npm run dev
```

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.11+, FastAPI, Pydantic, AsyncIO |
| **Frontend** | Next.js 14 (App Router), React 18, TypeScript |
| **Styling** | Tailwind CSS, shadcn/ui components |
| **State** | React hooks, localStorage |
| **Database** | SQLite (analytics) |
| **LLM** | Ollama (local) / OpenAI API |
| **Transport** | REST API + WebSocket |

---

## File Dependency Map

### Backend Dependencies

```
main.py
├── config.py (Settings)
├── prompts.py (Agent prompts)
├── llm/ (LLM integration)
│   ├── __init__.py → exports ChatMessage, LLMRouter
│   ├── router.py → uses base.py, ollama_client.py, openai_client.py
│   ├── base.py → defines BaseLLMClient, ChatMessage
│   ├── ollama_client.py → implements BaseLLMClient
│   └── openai_client.py → implements BaseLLMClient
├── tools/ (Tool system)
│   ├── __init__.py → exports ToolRegistry, get_registry
│   ├── registry.py → uses schemas.py
│   ├── schemas.py → ToolDefinition, ToolCall, ToolResult
│   └── api.py → REST routes for tools
├── diagnostics/ (All diagnostic tools)
│   ├── __init__.py → register_all_diagnostics()
│   │   └── imports all tool modules
│   ├── base.py → BaseDiagnostic, DiagnosticResult
│   ├── platform.py → Platform enum, CommandExecutor
│   └── [tool].py → individual tool implementations
└── analytics/ (Analytics module)
    ├── collector.py → AnalyticsCollector
    ├── storage.py → AnalyticsStorage (SQLite)
    ├── models.py → Session, Event, ToolEvent, etc.
    └── api.py → REST routes for analytics
```

### Frontend Dependencies

```
app/layout.tsx
├── components/theme-provider.tsx
├── components/ui/tooltip.tsx
├── components/layout/Header.tsx
└── globals.css

app/chat/page.tsx (Server Component)
├── lib/api.ts (listSessions, listTools)
└── app/chat/client.tsx (Client Component)
    ├── components/layout/Sidebar.tsx
    ├── components/chat/ChatWindow.tsx
    │   ├── hooks/use-chat.ts
    │   │   ├── hooks/use-websocket.ts
    │   │   │   └── lib/websocket.ts
    │   │   └── lib/api.ts (getSessionMessages)
    │   ├── components/chat/MessageBubble.tsx
    │   └── components/chat/ToolExecutionCard.tsx
    └── components/diagnostics/ManualToolPanel.tsx

hooks/use-chat.ts
├── hooks/use-websocket.ts → lib/websocket.ts
├── lib/api.ts
├── lib/utils.ts
└── types/index.ts
```

---

## Summary

TechTim(e) is a well-structured full-stack application that combines:

1. **Intelligent Diagnostics** - LLM-powered reasoning with structured OSI-layer troubleshooting
2. **Multi-Backend LLM** - Supports both local (Ollama) and cloud (OpenAI) with automatic fallback
3. **Rich Tool System** - 20+ diagnostic tools with cross-platform support
4. **Real-time Communication** - WebSocket for instant chat responses
5. **Comprehensive Analytics** - Session tracking, tool usage, and cost monitoring
6. **Modern Frontend** - Next.js with shadcn/ui for a polished user experience
7. **Dual Interface** - Both CLI and Web UI for different use cases

The architecture follows clean separation of concerns with clear module boundaries, making it maintainable and extensible for future enhancements.

