# Backend CLI Tool Calling Architecture Report

## Overview

The network diagnostics CLI implements a robust tool calling system that bridges LLM function calling with actual diagnostic execution. The system supports both OpenAI and Ollama backends with automatic fallback.

---

## Complete Architecture Diagram

### High-Level System Overview

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    TERMINAL (Rich Console)                                   │
│  ┌────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │  $ network-diag chat                                                                   │  │
│  │  Network Diagnostics Assistant                                                         │  │
│  │  Using model: gpt-4o-mini                                                              │  │
│  │  ─────────────────────────────────────────────────────────                             │  │
│  │  You> My internet is not working                                                       │  │
│  │  Thinking...                                                                           │  │
│  │  [Running] ping_gateway()                                                              │  │
│  │  ┌─────────────────────────────────────────────┐                                       │  │
│  │  │ ping_gateway result: Gateway unreachable... │                                       │  │
│  │  └─────────────────────────────────────────────┘                                       │  │
│  │  Assistant: Your gateway is unreachable. This indicates...                             │  │
│  └────────────────────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Complete Data Flow (Input → Processing → Output)

```
╔══════════════════════════════════════════════════════════════════════════════════════════════╗
║                                      USER INPUT PHASE                                        ║
╠══════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                              ║
║    ┌─────────────┐          ┌─────────────────┐          ┌───────────────────┐              ║
║    │   User      │  text    │   Rich.Prompt   │  string  │  Input Validation │              ║
║    │   Types     │ ───────► │   .ask()        │ ───────► │  (quit/commands)  │              ║
║    │   Message   │          │                 │          │                   │              ║
║    └─────────────┘          └─────────────────┘          └─────────┬─────────┘              ║
║                                                                     │                        ║
║                           ┌─────────────────────────────────────────┼─────────────────┐      ║
║                           │                                         │                 │      ║
║                           ▼                                         ▼                 ▼      ║
║                    ┌─────────────┐                           ┌─────────────┐   ┌──────────┐  ║
║                    │ /feedback   │                           │ /stats      │   │ quit/q   │  ║
║                    │ command     │                           │ command     │   │ exit     │  ║
║                    └──────┬──────┘                           └──────┬──────┘   └────┬─────┘  ║
║                           │                                         │               │        ║
║                           ▼                                         ▼               ▼        ║
║                    Prompt for                                 Show analytics   End session   ║
║                    feedback                                   summary          + feedback    ║
║                                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════╝
                                              │
                                              │ Normal message (not a command)
                                              ▼
╔══════════════════════════════════════════════════════════════════════════════════════════════╗
║                                   MESSAGE PROCESSING PHASE                                   ║
╠══════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                              ║
║    ┌──────────────────────────────────────────────────────────────────────────────────┐      ║
║    │                           ANALYTICS COLLECTOR                                    │      ║
║    │  ┌──────────────────┐                                                            │      ║
║    │  │ record_user_     │◄─────── User message recorded for session tracking         │      ║
║    │  │ message()        │                                                            │      ║
║    │  └──────────────────┘                                                            │      ║
║    └──────────────────────────────────────────────────────────────────────────────────┘      ║
║                                              │                                               ║
║                                              ▼                                               ║
║    ┌──────────────────────────────────────────────────────────────────────────────────┐      ║
║    │                            MESSAGE HISTORY (list[ChatMessage])                   │      ║
║    │  ┌─────────────────────────────────────────────────────────────────────────────┐ │      ║
║    │  │ [0] ChatMessage(role="system", content=diagnostic_agent_prompt)             │ │      ║
║    │  │ [1] ChatMessage(role="user", content="My internet is not working")    ◄─NEW │ │      ║
║    │  └─────────────────────────────────────────────────────────────────────────────┘ │      ║
║    └──────────────────────────────────────────────────────────────────────────────────┘      ║
║                                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════╝
                                              │
                                              ▼
╔══════════════════════════════════════════════════════════════════════════════════════════════╗
║                                    LLM ROUTING PHASE                                         ║
╠══════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                              ║
║    ┌──────────────────────────────────────────────────────────────────────────────────┐      ║
║    │                              LLM ROUTER (router.py)                              │      ║
║    │                                                                                  │      ║
║    │   Input:                                                                         │      ║
║    │   ├── messages: list[ChatMessage]                                                │      ║
║    │   ├── tools: list[ToolDefinition]  ◄── from registry.get_all_definitions()      │      ║
║    │   └── temperature: 0.3                                                           │      ║
║    │                                                                                  │      ║
║    │   ┌─────────────────────────────────────────────────────────────────────────┐    │      ║
║    │   │                     BACKEND SELECTION LOGIC                             │    │      ║
║    │   │                                                                         │    │      ║
║    │   │   settings.llm_backend = "ollama" (default)                             │    │      ║
║    │   │                     │                                                   │    │      ║
║    │   │                     ▼                                                   │    │      ║
║    │   │         ┌───────────────────────┐                                       │    │      ║
║    │   │         │ ollama.is_available() │                                       │    │      ║
║    │   │         └───────────┬───────────┘                                       │    │      ║
║    │   │                     │                                                   │    │      ║
║    │   │           ┌─────────┴─────────┐                                         │    │      ║
║    │   │           │                   │                                         │    │      ║
║    │   │           ▼                   ▼                                         │    │      ║
║    │   │        [True]             [False]                                       │    │      ║
║    │   │           │                   │                                         │    │      ║
║    │   │           ▼                   ▼                                         │    │      ║
║    │   │    Use Ollama         ┌──────────────────────┐                          │    │      ║
║    │   │                       │ openai.is_available()│                          │    │      ║
║    │   │                       └──────────┬───────────┘                          │    │      ║
║    │   │                                  │                                      │    │      ║
║    │   │                        ┌─────────┴─────────┐                            │    │      ║
║    │   │                        ▼                   ▼                            │    │      ║
║    │   │                     [True]             [False]                          │    │      ║
║    │   │                        │                   │                            │    │      ║
║    │   │                        ▼                   ▼                            │    │      ║
║    │   │                 Use OpenAI          RuntimeError:                       │    │      ║
║    │   │                 (fallback)          "No LLM available"                  │    │      ║
║    │   │                        │                                                │    │      ║
║    │   │                        ▼                                                │    │      ║
║    │   │                 record_fallback()                                       │    │      ║
║    │   │                 in analytics                                            │    │      ║
║    │   │                                                                         │    │      ║
║    │   └─────────────────────────────────────────────────────────────────────────┘    │      ║
║    └──────────────────────────────────────────────────────────────────────────────────┘      ║
║                                              │                                               ║
║                                              ▼                                               ║
║    ┌─────────────────────────────────────────┬────────────────────────────────────────┐      ║
║    │                                         │                                        │      ║
║    │         OLLAMA CLIENT                   │          OPENAI CLIENT                 │      ║
║    │         (ollama_client.py)              │          (openai_client.py)            │      ║
║    │                                         │                                        │      ║
║    │   ┌─────────────────────────┐           │    ┌─────────────────────────┐         │      ║
║    │   │ Convert ChatMessage to  │           │    │ Convert ChatMessage to  │         │      ║
║    │   │ Ollama format:          │           │    │ OpenAI format:          │         │      ║
║    │   │                         │           │    │                         │         │      ║
║    │   │ {                       │           │    │ {                       │         │      ║
║    │   │   "role": "user",       │           │    │   "role": "user",       │         │      ║
║    │   │   "content": "..."      │           │    │   "content": "..."      │         │      ║
║    │   │ }                       │           │    │ }                       │         │      ║
║    │   └─────────────────────────┘           │    └─────────────────────────┘         │      ║
║    │                                         │                                        │      ║
║    │   ┌─────────────────────────┐           │    ┌─────────────────────────┐         │      ║
║    │   │ Convert ToolDefinition  │           │    │ Convert ToolDefinition  │         │      ║
║    │   │ to schema:              │           │    │ to schema:              │         │      ║
║    │   │                         │           │    │                         │         │      ║
║    │   │ d.to_ollama_schema()    │           │    │ d.to_openai_schema()    │         │      ║
║    │   │ (same as OpenAI)        │           │    │                         │         │      ║
║    │   └─────────────────────────┘           │    └─────────────────────────┘         │      ║
║    │                                         │                                        │      ║
║    │   ┌─────────────────────────┐           │    ┌─────────────────────────┐         │      ║
║    │   │ HTTP POST               │           │    │ OpenAI SDK              │         │      ║
║    │   │ /api/chat               │           │    │ client.chat.completions │         │      ║
║    │   │                         │           │    │ .create()               │         │      ║
║    │   │ payload = {             │           │    │                         │         │      ║
║    │   │   "model": "ministral", │           │    │ kwargs = {              │         │      ║
║    │   │   "messages": [...],    │           │    │   "model": "gpt-4o-mini"│         │      ║
║    │   │   "tools": [...],       │           │    │   "messages": [...],    │         │      ║
║    │   │   "stream": false       │           │    │   "tools": [...],       │         │      ║
║    │   │ }                       │           │    │   "tool_choice": "auto" │         │      ║
║    │   └─────────────────────────┘           │    │ }                       │         │      ║
║    │                                         │    └─────────────────────────┘         │      ║
║    └─────────────────────────────────────────┴────────────────────────────────────────┘      ║
║                                              │                                               ║
║                                              ▼                                               ║
║    ┌──────────────────────────────────────────────────────────────────────────────────┐      ║
║    │                              LLM RESPONSE PARSING                                │      ║
║    │                                                                                  │      ║
║    │   ChatResponse {                                                                 │      ║
║    │     message: ChatMessage {                                                       │      ║
║    │       role: "assistant",                                                         │      ║
║    │       content: null | "Let me check your network...",                            │      ║
║    │       tool_calls: [                     ◄── May contain 0+ tool calls            │      ║
║    │         ToolCall {                                                               │      ║
║    │           id: "call_abc123",                                                     │      ║
║    │           name: "ping_gateway",                                                  │      ║
║    │           arguments: {}                                                          │      ║
║    │         }                                                                        │      ║
║    │       ]                                                                          │      ║
║    │     },                                                                           │      ║
║    │     finish_reason: "tool_calls" | "stop",                                        │      ║
║    │     usage: { prompt_tokens: 450, completion_tokens: 25 }                         │      ║
║    │   }                                                                              │      ║
║    │                                                                                  │      ║
║    │   Analytics: record_llm_call(duration_ms, tokens, model_name)                    │      ║
║    │                                                                                  │      ║
║    └──────────────────────────────────────────────────────────────────────────────────┘      ║
║                                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════╝
                                              │
                              ┌───────────────┴───────────────┐
                              │                               │
                              ▼                               ▼
               response.has_tool_calls?              response.has_tool_calls?
                      [TRUE]                               [FALSE]
                              │                               │
                              ▼                               │
╔══════════════════════════════════════════════════════════╗  │
║                   TOOL EXECUTION PHASE                   ║  │
╠══════════════════════════════════════════════════════════╣  │
║                                                          ║  │
║  ┌────────────────────────────────────────────────────┐  ║  │
║  │ messages.append(response.message)                  │  ║  │
║  │ # Add assistant message with tool_calls to history │  ║  │
║  └────────────────────────────────────────────────────┘  ║  │
║                         │                                ║  │
║                         ▼                                ║  │
║  ┌────────────────────────────────────────────────────┐  ║  │
║  │        FOR EACH tool_call in tool_calls:           │  ║  │
║  │                                                    │  ║  │
║  │  ┌──────────────────────────────────────────────┐  │  ║  │
║  │  │ DISPLAY TO USER (Rich Console):              │  │  ║  │
║  │  │                                              │  │  ║  │
║  │  │ [yellow]Running:[/yellow] ping_gateway()    │  │  ║  │
║  │  └──────────────────────────────────────────────┘  │  ║  │
║  │                         │                          │  ║  │
║  │                         ▼                          │  ║  │
║  │  ┌──────────────────────────────────────────────┐  │  ║  │
║  │  │            TOOL REGISTRY EXECUTE             │  │  ║  │
║  │  │            (registry.py)                     │  │  ║  │
║  │  │                                              │  │  ║  │
║  │  │  result = await registry.execute(tool_call)  │  │  ║  │
║  │  │                                              │  │  ║  │
║  │  │  ┌────────────────────────────────────────┐  │  │  ║  │
║  │  │  │ 1. Lookup: _tools[tool_call.name]      │  │  │  ║  │
║  │  │  │                                        │  │  │  ║  │
║  │  │  │ 2. Start timer: time.perf_counter()    │  │  │  ║  │
║  │  │  │                                        │  │  │  ║  │
║  │  │  │ 3. Execute:                            │  │  │  ║  │
║  │  │  │    if async: await tool(**args)        │  │  │  ║  │
║  │  │  │    else: tool(**args)                  │  │  │  ║  │
║  │  │  │                                        │  │  │  ║  │
║  │  │  │ 4. Convert result:                     │  │  │  ║  │
║  │  │  │    result.to_llm_response()            │  │  │  ║  │
║  │  │  │                                        │  │  │  ║  │
║  │  │  │ 5. Record analytics:                   │  │  │  ║  │
║  │  │  │    record_tool_call(name, duration,    │  │  │  ║  │
║  │  │  │                     success, args)     │  │  │  ║  │
║  │  │  │                                        │  │  │  ║  │
║  │  │  │ 6. Return ToolResult                   │  │  │  ║  │
║  │  │  └────────────────────────────────────────┘  │  │  ║  │
║  │  └──────────────────────────────────────────────┘  │  ║  │
║  │                         │                          │  ║  │
║  │                         ▼                          │  ║  │
║  │  ┌──────────────────────────────────────────────┐  │  ║  │
║  │  │            DIAGNOSTIC EXECUTION              │  │  ║  │
║  │  │                                              │  │  ║  │
║  │  │  ┌──────────────────────────────────────┐    │  │  ║  │
║  │  │  │ ping_gateway() in connectivity.py   │    │  │  ║  │
║  │  │  │                                      │    │  │  ║  │
║  │  │  │  1. Detect platform (macOS/Windows) │    │  │  ║  │
║  │  │  │  2. Get gateway from routing table  │    │  │  ║  │
║  │  │  │  3. Execute: ping -c 4 192.168.1.1  │    │  │  ║  │
║  │  │  │  4. Parse output (packet loss, RTT) │    │  │  ║  │
║  │  │  │  5. Generate suggestions            │    │  │  ║  │
║  │  │  │  6. Return DiagnosticResult         │    │  │  ║  │
║  │  │  └──────────────────────────────────────┘    │  │  ║  │
║  │  └──────────────────────────────────────────────┘  │  ║  │
║  │                         │                          │  ║  │
║  │                         ▼                          │  ║  │
║  │  ┌──────────────────────────────────────────────┐  │  ║  │
║  │  │ DISPLAY RESULT PANEL (Rich Console):         │  │  ║  │
║  │  │                                              │  │  ║  │
║  │  │ ╭─────────────────────────────────────────╮  │  │  ║  │
║  │  │ │ ping_gateway result                     │  │  │  ║  │
║  │  │ │ Gateway: 192.168.1.1                    │  │  │  ║  │
║  │  │ │ Reachable: false                        │  │  │  ║  │
║  │  │ │ Packet Loss: 100%                       │  │  │  ║  │
║  │  │ ╰─────────────────────────────────────────╯  │  │  ║  │
║  │  └──────────────────────────────────────────────┘  │  ║  │
║  │                         │                          │  ║  │
║  │                         ▼                          │  ║  │
║  │  ┌──────────────────────────────────────────────┐  │  ║  │
║  │  │ APPEND TOOL RESULT TO MESSAGE HISTORY:       │  │  ║  │
║  │  │                                              │  │  ║  │
║  │  │ messages.append(ChatMessage(                 │  │  ║  │
║  │  │   role="tool",                               │  │  ║  │
║  │  │   content=result.content,                    │  │  ║  │
║  │  │   tool_call_id=tool_call.id,                 │  │  ║  │
║  │  │   name=tool_call.name                        │  │  ║  │
║  │  │ ))                                           │  │  ║  │
║  │  └──────────────────────────────────────────────┘  │  ║  │
║  │                                                    │  ║  │
║  └────────────────────────────────────────────────────┘  ║  │
║                         │                                ║  │
║                         ▼                                ║  │
║  ┌────────────────────────────────────────────────────┐  ║  │
║  │ SECOND LLM CALL (with tool results in context):    │  ║  │
║  │                                                    │  ║  │
║  │ response = await llm_router.chat(messages, tools)  │  ║  │
║  │                                                    │  ║  │
║  │ Messages now contain:                              │  ║  │
║  │ [0] system: diagnostic agent prompt                │  ║  │
║  │ [1] user: "My internet is not working"             │  ║  │
║  │ [2] assistant: (tool_calls=[ping_gateway])         │  ║  │
║  │ [3] tool: "Gateway unreachable, 100% loss..."      │  ║  │
║  │                                                    │  ║  │
║  │ LLM generates final analysis based on tool data    │  ║  │
║  └────────────────────────────────────────────────────┘  ║  │
║                         │                                ║  │
╚═════════════════════════╪════════════════════════════════╝  │
                          │                                   │
                          └───────────────┬───────────────────┘
                                          │
                                          ▼
╔══════════════════════════════════════════════════════════════════════════════════════════════╗
║                                     OUTPUT PHASE                                             ║
╠══════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                              ║
║    ┌──────────────────────────────────────────────────────────────────────────────────┐      ║
║    │ APPEND FINAL RESPONSE TO HISTORY:                                                │      ║
║    │                                                                                  │      ║
║    │ messages.append(response.message)                                                │      ║
║    └──────────────────────────────────────────────────────────────────────────────────┘      ║
║                                              │                                               ║
║                                              ▼                                               ║
║    ┌──────────────────────────────────────────────────────────────────────────────────┐      ║
║    │ DISPLAY ASSISTANT RESPONSE (Rich Console + Markdown):                            │      ║
║    │                                                                                  │      ║
║    │  [bold blue]Assistant[/bold blue]                                                │      ║
║    │                                                                                  │      ║
║    │  Based on the diagnostic results, your **gateway is unreachable**. This          │      ║
║    │  typically indicates one of the following issues:                                │      ║
║    │                                                                                  │      ║
║    │  1. Your router/modem may be powered off or disconnected                         │      ║
║    │  2. The Ethernet cable may be unplugged                                          │      ║
║    │  3. WiFi may be disabled on your computer                                        │      ║
║    │                                                                                  │      ║
║    │  **Recommended steps:**                                                          │      ║
║    │  - Check if your router has power lights on                                      │      ║
║    │  - Try restarting your router                                                    │      ║
║    │  - Verify your network cable connections                                         │      ║
║    │                                                                                  │      ║
║    └──────────────────────────────────────────────────────────────────────────────────┘      ║
║                                              │                                               ║
║                                              ▼                                               ║
║    ┌──────────────────────────────────────────────────────────────────────────────────┐      ║
║    │ RESOLUTION DETECTION (optional):                                                 │      ║
║    │                                                                                  │      ║
║    │ if detect_resolution_signal(user_input):                                         │      ║
║    │     # Patterns: "thanks", "works", "fixed", "resolved", etc.                     │      ║
║    │     prompt_for_feedback()                                                        │      ║
║    │                                                                                  │      ║
║    └──────────────────────────────────────────────────────────────────────────────────┘      ║
║                                              │                                               ║
║                                              ▼                                               ║
║                                      ┌─────────────┐                                         ║
║                                      │  LOOP BACK  │                                         ║
║                                      │  TO INPUT   │                                         ║
║                                      │   PHASE     │                                         ║
║                                      └─────────────┘                                         ║
║                                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════╝
```

### Message History Evolution (Detailed Example)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                            MESSAGE HISTORY THROUGH CONVERSATION                                │
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                │
│  INITIAL STATE (after session start):                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ messages = [                                                                             │  │
│  │   ChatMessage(role="system", content="You are a network diagnostic agent...")           │  │
│  │ ]                                                                                        │  │
│  └──────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                │                                               │
│                                                ▼                                               │
│  AFTER USER INPUT:                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ messages = [                                                                             │  │
│  │   ChatMessage(role="system", content="You are a network diagnostic agent..."),          │  │
│  │   ChatMessage(role="user", content="My WiFi keeps disconnecting")          ◄── NEW      │  │
│  │ ]                                                                                        │  │
│  └──────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                │                                               │
│                                                ▼                                               │
│  AFTER LLM RETURNS TOOL CALLS:                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ messages = [                                                                             │  │
│  │   ChatMessage(role="system", content="..."),                                             │  │
│  │   ChatMessage(role="user", content="My WiFi keeps disconnecting"),                       │  │
│  │   ChatMessage(role="assistant", content=None, tool_calls=[                  ◄── NEW      │  │
│  │     ToolCall(id="call_1", name="check_adapter_status", arguments={}),                    │  │
│  │     ToolCall(id="call_2", name="get_ip_config", arguments={})                            │  │
│  │   ])                                                                                     │  │
│  │ ]                                                                                        │  │
│  └──────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                │                                               │
│                                                ▼                                               │
│  AFTER TOOL EXECUTION:                                                                         │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ messages = [                                                                             │  │
│  │   ChatMessage(role="system", content="..."),                                             │  │
│  │   ChatMessage(role="user", content="My WiFi keeps disconnecting"),                       │  │
│  │   ChatMessage(role="assistant", content=None, tool_calls=[...]),                         │  │
│  │   ChatMessage(role="tool", tool_call_id="call_1", name="check_adapter_status",           │  │
│  │               content="WiFi adapter: en0, Status: active, Signal: -65dBm"),   ◄── NEW    │  │
│  │   ChatMessage(role="tool", tool_call_id="call_2", name="get_ip_config",                  │  │
│  │               content="IP: 192.168.1.45, Gateway: 192.168.1.1, DNS: 8.8.8.8") ◄── NEW    │  │
│  │ ]                                                                                        │  │
│  └──────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                │                                               │
│                                                ▼                                               │
│  AFTER FINAL LLM RESPONSE:                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ messages = [                                                                             │  │
│  │   ChatMessage(role="system", content="..."),                                             │  │
│  │   ChatMessage(role="user", content="My WiFi keeps disconnecting"),                       │  │
│  │   ChatMessage(role="assistant", content=None, tool_calls=[...]),                         │  │
│  │   ChatMessage(role="tool", tool_call_id="call_1", name="check_adapter_status", ...),     │  │
│  │   ChatMessage(role="tool", tool_call_id="call_2", name="get_ip_config", ...),            │  │
│  │   ChatMessage(role="assistant", content="Your WiFi adapter is active with    ◄── NEW    │  │
│  │               a signal strength of -65dBm. This is a moderate signal...")               │  │
│  │ ]                                                                                        │  │
│  └──────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Tool Schema Conversion Flow

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              TOOL SCHEMA CONVERSION                                            │
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                │
│  REGISTRATION (diagnostics/__init__.py):                                                       │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ registry.register(                                                                       │  │
│  │     name="ping_gateway",                                                                 │  │
│  │     description="Test connectivity to the default gateway...",                           │  │
│  │     parameters=[                                                                         │  │
│  │         ToolParameter(name="gateway", type="string", required=False, ...),              │  │
│  │         ToolParameter(name="count", type="number", required=False, ...)                 │  │
│  │     ]                                                                                    │  │
│  │ )(ping_gateway)                                                                          │  │
│  └──────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                │                                               │
│                                                ▼                                               │
│  STORED AS ToolDefinition:                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ ToolDefinition(                                                                          │  │
│  │     name="ping_gateway",                                                                 │  │
│  │     description="Test connectivity to the default gateway...",                           │  │
│  │     parameters=[ToolParameter(...), ToolParameter(...)]                                  │  │
│  │ )                                                                                        │  │
│  └──────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                │                                               │
│                          ┌─────────────────────┴─────────────────────┐                         │
│                          ▼                                           ▼                         │
│  ┌─────────────────────────────────────────┐  ┌─────────────────────────────────────────────┐  │
│  │ to_openai_schema() / to_ollama_schema() │  │           SENT TO LLM API                   │  │
│  │                                         │  │                                             │  │
│  │ {                                       │  │  {                                          │  │
│  │   "type": "function",                   │  │    "type": "function",                      │  │
│  │   "function": {                         │  │    "function": {                            │  │
│  │     "name": "ping_gateway",             │  │      "name": "ping_gateway",                │  │
│  │     "description": "Test connectivity   │  │      "description": "...",                  │  │
│  │       to the default gateway...",       │  │      "parameters": {                        │  │
│  │     "parameters": {                     │  │        "type": "object",                    │  │
│  │       "type": "object",                 │  │        "properties": {                      │  │
│  │       "properties": {                   │  │          "gateway": {                       │  │
│  │         "gateway": {                    │  │            "type": "string",                │  │
│  │           "type": "string",             │  │            "description": "..."             │  │
│  │           "description": "Gateway IP"   │  │          },                                 │  │
│  │         },                              │  │          "count": {                         │  │
│  │         "count": {                      │  │            "type": "number",                │  │
│  │           "type": "number",             │  │            "description": "..."             │  │
│  │           "description": "Packet count" │  │          }                                  │  │
│  │         }                               │  │        },                                   │  │
│  │       },                                │  │        "required": []                       │  │
│  │       "required": []                    │  │      }                                      │  │
│  │     }                                   │  │    }                                        │  │
│  │   }                                     │  │  }                                          │  │
│  │ }                                       │  │                                             │  │
│  └─────────────────────────────────────────┘  └─────────────────────────────────────────────┘  │
│                                                                                                │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Dependency Graph

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               FILE DEPENDENCIES                                                │
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                │
│                              ┌────────────────────────┐                                        │
│                              │     backend/cli.py     │                                        │
│                              │    (Entry Point)       │                                        │
│                              └───────────┬────────────┘                                        │
│                                          │                                                     │
│            ┌─────────────────────────────┼─────────────────────────────┐                       │
│            │                             │                             │                       │
│            ▼                             ▼                             ▼                       │
│   ┌─────────────────┐          ┌─────────────────┐          ┌──────────────────┐              │
│   │  backend/llm/   │          │ backend/tools/  │          │   backend/       │              │
│   │   router.py     │          │  registry.py    │          │  diagnostics/    │              │
│   └────────┬────────┘          └────────┬────────┘          │   __init__.py    │              │
│            │                            │                   └────────┬─────────┘              │
│      ┌─────┴─────┐                      │                            │                        │
│      │           │                      │                            │                        │
│      ▼           ▼                      ▼                   ┌────────┴────────┐               │
│ ┌─────────┐ ┌─────────┐         ┌─────────────┐             │                 │               │
│ │ openai_ │ │ ollama_ │         │  schemas.py │             ▼                 ▼               │
│ │client.py│ │client.py│         │             │      ┌────────────┐    ┌────────────┐         │
│ └────┬────┘ └────┬────┘         │ToolParameter│      │ adapter.py │    │   dns.py   │         │
│      │           │              │ToolDefinition      │            │    │            │         │
│      │           │              │ToolCall     │      │ ip_config  │    │connectivity│         │
│      │           │              │ToolResult   │      │   .py      │    │   .py      │         │
│      ▼           ▼              └─────────────┘      └────────────┘    └────────────┘         │
│ ┌─────────────────────┐                                     │                                  │
│ │   backend/llm/      │                                     ▼                                  │
│ │     base.py         │                              ┌─────────────────┐                       │
│ │                     │                              │    base.py      │                       │
│ │  ChatMessage        │                              │ DiagnosticResult│                       │
│ │  ChatResponse       │                              │ BaseDiagnostic  │                       │
│ │  BaseLLMClient      │                              └────────┬────────┘                       │
│ └─────────────────────┘                                       │                                │
│                                                               ▼                                │
│                                                        ┌─────────────┐                         │
│                                                        │ platform.py │                         │
│                                                        │             │                         │
│                                                        │  Platform   │                         │
│                                                        │  (enum)     │                         │
│                                                        │             │                         │
│                                                        │ Command-    │                         │
│                                                        │ Executor    │                         │
│                                                        └─────────────┘                         │
│                                                                                                │
│  ┌────────────────────────────────────────────────────────────────────────────────────────┐    │
│  │                              ANALYTICS (cross-cutting)                                 │    │
│  │                                                                                        │    │
│  │   analytics/                                                                           │    │
│  │   ├── collector.py  ◄─── Used by: cli.py, registry.py, router.py                      │    │
│  │   ├── storage.py    ◄─── SQLite persistence                                            │    │
│  │   └── models.py     ◄─── SessionOutcome, IssueCategory                                 │    │
│  │                                                                                        │    │
│  └────────────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                                │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Tool Registry (`backend/tools/registry.py`)

The `ToolRegistry` class is the central hub for managing diagnostic tools.

**Key Features:**
- Decorator-based tool registration
- Supports both sync and async functions
- Converts results to LLM-friendly formats
- Integrated analytics tracking
- Schema generation for OpenAI and Ollama

```python
class ToolRegistry:
    _tools: dict[str, Callable[..., Any]]       # Function references
    _definitions: dict[str, ToolDefinition]      # Schema definitions
    _analytics: AnalyticsCollector | None        # Optional analytics
```

**Tool Execution Flow:**
1. Receive `ToolCall` with name and arguments
2. Look up registered function
3. Track execution start time
4. Execute function (handles async/sync)
5. Convert result to string (via `to_llm_response()` or JSON)
6. Record analytics (duration, success, arguments, result)
7. Return `ToolResult`

### 2. Schema Definitions (`backend/tools/schemas.py`)

Four Pydantic models define the tool calling contract:

| Model | Purpose |
|-------|---------|
| `ToolParameter` | Parameter definition (name, type, description, required, default, enum) |
| `ToolDefinition` | Full tool spec with name, description, parameters |
| `ToolCall` | LLM request to execute a tool (id, name, arguments) |
| `ToolResult` | Execution result (tool_call_id, name, content, success) |

**Schema Conversion:**

```python
def to_openai_schema(self) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }
    }
```

### 3. LLM Router (`backend/llm/router.py`)

Routes requests to available LLM backends with automatic fallback.

**Features:**
- Lazy client initialization
- Preference-based backend selection
- Automatic fallback with analytics tracking
- Usage statistics (tokens, timing)

**Backend Selection Logic:**
```
1. Try preferred backend (from settings)
2. If unavailable, fallback to alternative
3. Record fallback event in analytics
4. Cache active client for session
```

---

## Tool Calling Flow (cli.py)

### Main Chat Loop Sequence

```
1. User enters message
   └── Record in analytics: record_user_message()

2. Send to LLM with tool definitions
   └── llm_router.chat(messages, tools)
       └── Converts tools to OpenAI/Ollama schema

3. Check if response has tool calls
   └── response.has_tool_calls → True

4. For each tool_call in response.message.tool_calls:
   ├── Log: "Executing tool: {name} with args: {args}"
   ├── Display: "[yellow]Running:[/yellow] {name}({args})"
   ├── Execute: tool_registry.execute(tool_call)
   ├── Display result panel
   └── Append tool response to messages:
       └── ChatMessage(role="tool", content=result, tool_call_id=id)

5. Get final response (with tool results in context)
   └── llm_router.chat(messages, tools)

6. Display assistant response
   └── Markdown rendered via Rich
```

### Message Flow Example

```python
# Initial user message
messages = [
    ChatMessage(role="system", content=system_prompt),
    ChatMessage(role="user", content="My internet is slow"),
]

# LLM responds with tool call
response = await llm_router.chat(messages, tools)
# → message.tool_calls = [ToolCall(name="ping_gateway", ...)]

# Add assistant message with tool calls
messages.append(response.message)

# Execute tool and add result
result = await tool_registry.execute(tool_call)
messages.append(ChatMessage(
    role="tool",
    content=result.content,
    tool_call_id=tool_call.id,
    name=tool_call.name,
))

# Get final response with tool context
final_response = await llm_router.chat(messages, tools)
```

---

## LLM Client Implementations

### OpenAI Client (`backend/llm/openai_client.py`)

**Message Conversion:**
- Tool calls serialized as JSON strings
- Uses `tool_choice: "auto"` for automatic tool selection
- Parses response `tool_calls` back to `ToolCall` objects

**Key Details:**
- Arguments are JSON-stringified for API: `json.dumps(tc.arguments)`
- Response arguments are JSON-parsed: `json.loads(args)`
- Supports full message history with proper role handling

### Ollama Client (`backend/llm/ollama_client.py`)

**Key Differences from OpenAI:**
- Arguments passed as objects (not JSON strings)
- Uses HTTP via httpx with 120s timeout
- Same schema format as OpenAI (via `to_ollama_schema()`)

**Debug Logging:**
```python
_ollama_dbg("ollama:chat:request", "Sending to Ollama", {...})
_ollama_dbg("ollama:chat:response", "Ollama response received", {...})
```

---

## Tool Registration Pattern

Tools are registered in `backend/diagnostics/__init__.py`:

```python
def register_all_diagnostics(registry) -> None:
    from .adapter import check_adapter_status
    
    registry.register(
        name="check_adapter_status",
        description="Check if network adapters are enabled...",
        parameters=[
            ToolParameter(
                name="interface_name",
                type="string",
                description="Specific interface to check...",
                required=False,
            ),
        ],
    )(check_adapter_status)
```

**Registered Tools:**

| Tool Name | OSI Layer | Description |
|-----------|-----------|-------------|
| `check_adapter_status` | Physical/Link | Check network adapter status |
| `get_ip_config` | Network | Get IP/subnet/gateway/DNS config |
| `ping_gateway` | Network | Test gateway connectivity |
| `ping_dns` | Network | Test external connectivity (8.8.8.8, 1.1.1.1) |
| `test_dns_resolution` | Application | Test DNS name resolution |
| `enable_wifi` | Physical | Enable WiFi adapter |

---

## Result Formatting

Tools return `DiagnosticResult` with a `to_llm_response()` method:

```python
class DiagnosticResult(BaseModel):
    success: bool
    data: dict[str, Any]
    raw_output: str | None
    error: str | None
    suggestions: list[str] | None
    
    def to_llm_response(self) -> str:
        # Formats data + suggestions for LLM consumption
```

The registry handles conversion:
```python
if hasattr(result, "to_llm_response"):
    content = result.to_llm_response()
elif hasattr(result, "model_dump_json"):
    content = result.model_dump_json(indent=2)
else:
    content = str(result)
```

---

## Analytics Integration

Tool execution is tracked via `AnalyticsCollector`:

```python
# Recorded on every tool execution
analytics.record_tool_call(
    tool_name=tool_call.name,
    duration_ms=duration_ms,
    success=success,
    error_message=error_message,
    arguments=tool_call.arguments,
    result_summary=result_summary[:200],  # Truncated
)
```

**Tracked Metrics:**
- Tool name and arguments
- Execution duration (ms)
- Success/failure status
- Error messages
- Result summary (first 200 chars)

---

## Error Handling

### Unknown Tool
```python
if tool is None:
    return ToolResult(
        content=f"Error: Unknown tool '{tool_call.name}'",
        success=False,
    )
```

### Execution Error
```python
except Exception as e:
    success = False
    error_message = str(e)
    content = f"Error executing tool: {error_message}"
    logger.exception(f"Tool {tool_call.name} failed: {e}")
```

### LLM Fallback
```python
if self.preferred == "ollama":
    if not await self.ollama.is_available():
        # Fallback to OpenAI
        self._had_fallback = True
        analytics.record_fallback(
            from_backend="ollama",
            to_backend="openai",
            reason="Ollama not available"
        )
```

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `network-diag chat` | Interactive AI-assisted troubleshooting |
| `network-diag check <diagnostic>` | Run single diagnostic (adapter, ip, gateway, dns-ping, dns-resolve) |
| `network-diag ladder` | Run full diagnostic ladder (all checks in sequence) |

### Special Chat Commands:
- `/feedback` — Rate session and start new one
- `/stats` — Show analytics summary
- `quit/exit/q` — Exit with feedback prompt

---

## Summary

**Strengths:**
1. Clean separation of concerns (registry, schemas, clients, diagnostics)
2. Unified interface for OpenAI and Ollama
3. Comprehensive analytics tracking
4. Async-first design with sync compatibility
5. Rich terminal output with proper formatting

**Current Implementation:**
- Single-turn tool execution (no parallel tool calls)
- Tool results immediately fed back to LLM for response
- All diagnostics registered at startup via `register_all_diagnostics()`

**Key Files:**
- `backend/cli.py` — Main chat loop and tool orchestration
- `backend/tools/registry.py` — Tool registration and execution
- `backend/tools/schemas.py` — Pydantic models for tool contract
- `backend/llm/router.py` — LLM backend routing
- `backend/diagnostics/__init__.py` — Tool registration declarations

