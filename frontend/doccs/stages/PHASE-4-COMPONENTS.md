# Phase 4: Component Implementation

Building all UI components from the specs in `doccs/components/`.

---

## Overview

Phase 4 is divided into **5 sub-phases**, each building a logical group of components:

| Sub-Phase | Components | Dependencies |
|-----------|------------|--------------|
| 4.1 | Layout (Header, Sidebar, MobileSidebar) | Phase 3 hooks |
| 4.2 | Chat (MessageBubble, ToolExecutionCard, ChatWindow) | Layout components |
| 4.3 | Diagnostics (ToolCard, OSILadderViz, ManualToolPanel) | Types, utilities |
| 4.4 | Analytics (SummaryCards, SessionsChart, ToolStatsTable) | API functions |
| 4.5 | Pages (Home, Chat, Dashboard, History) | All components |

**Total components: 16** (including hooks for headless patterns)

---

## Phase 4.1: Layout Components

### Components to Build

| Component | File | Spec |
|-----------|------|------|
| Header | `components/layout/Header.tsx` | [Header.md](../components/layout/Header.md) |
| Sidebar | `components/layout/Sidebar.tsx` | [Sidebar.md](../components/layout/Sidebar.md) |
| MobileSidebar | `components/layout/MobileSidebar.tsx` | [Sidebar.md](../components/layout/Sidebar.md) |

### Implementation Order

1. **Header** - Update existing with mobile menu and connection status
2. **Sidebar** - Session list with search/filter
3. **MobileSidebar** - Sheet wrapper for mobile

### Required shadcn/ui Components

```bash
# Already installed from Phase 1
npx shadcn@latest add dropdown-menu sheet
```

### Verification

```bash
npm run type-check && npm run lint && npm run build
```

---

## Phase 4.2: Chat Components

### Components to Build

| Component | File | Spec |
|-----------|------|------|
| MessageBubble | `components/chat/MessageBubble.tsx` | [MessageBubble.md](../components/chat/MessageBubble.md) |
| ToolExecutionCard | `components/chat/ToolExecutionCard.tsx` | [ToolExecutionCard.md](../components/chat/ToolExecutionCard.md) |
| ChatWindow | `components/chat/ChatWindow.tsx` | [ChatWindow.md](../components/chat/ChatWindow.md) |

### Hooks to Build

| Hook | File | Used By |
|------|------|---------|
| useToolExecution | `hooks/use-tool-execution.ts` | ToolExecutionCard |

### Implementation Order

1. **MessageBubble** - Single message display with markdown
2. **useToolExecution hook** - Headless state for tool execution
3. **ToolExecutionCard** - Tool execution status card
4. **ChatWindow** - Main chat container using all above

### Required Dependencies

```bash
npm install react-markdown remark-gfm
```

### Verification

```bash
npm run type-check && npm run lint && npm run build
```

---

## Phase 4.3: Diagnostics Components

### Components to Build

| Component | File | Spec |
|-----------|------|------|
| ToolCard | `components/diagnostics/ToolCard.tsx` | [ToolCard.md](../components/diagnostics/ToolCard.md) |
| OSILadderViz | `components/diagnostics/OSILadderViz.tsx` | [OSILadderViz.md](../components/diagnostics/OSILadderViz.md) |
| ManualToolPanel | `components/diagnostics/ManualToolPanel.tsx` | [ManualToolPanel.md](../components/diagnostics/ManualToolPanel.md) |

### Hooks to Build

| Hook | File | Used By |
|------|------|---------|
| useOSILadder | `hooks/use-osi-ladder.ts` | OSILadderViz, Chat Page |
| useManualToolPanel | `hooks/use-manual-tool-panel.ts` | ManualToolPanel |

### Implementation Order

1. **useOSILadder hook** - Layer state management
2. **OSILadderViz** - Visual layer display
3. **ToolCard** - Single tool with parameters
4. **useManualToolPanel hook** - Tool panel state
5. **ManualToolPanel** - Tool list with categories

### Verification

```bash
npm run type-check && npm run lint && npm run build
```

---

## Phase 4.4: Analytics Components

### Components to Build

| Component | File | Spec |
|-----------|------|------|
| SummaryCards | `components/analytics/SummaryCards.tsx` | [SummaryCards.md](../components/analytics/SummaryCards.md) |
| SessionsChart | `components/analytics/SessionsChart.tsx` | [SessionsChart.md](../components/analytics/SessionsChart.md) |
| CategoryChart | `components/analytics/SessionsChart.tsx` | [SessionsChart.md](../components/analytics/SessionsChart.md) |
| ToolUsageChart | `components/analytics/SessionsChart.tsx` | [SessionsChart.md](../components/analytics/SessionsChart.md) |
| ToolStatsTable | `components/analytics/ToolStatsTable.tsx` | [ToolStatsTable.md](../components/analytics/ToolStatsTable.md) |
| DateRangePicker | `components/analytics/DateRangePicker.tsx` | [dashboard-page.md](../components/pages/dashboard-page.md) |

### Implementation Order

1. **SummaryCards** - Metric cards grid
2. **SessionsChart** - Line/area chart for sessions
3. **CategoryChart** - Pie chart for categories
4. **ToolUsageChart** - Bar chart for tools
5. **ToolStatsTable** - Sortable statistics table
6. **DateRangePicker** - Date range selector

### Required Dependencies

```bash
# recharts already in Phase 1
npm install recharts
```

### Verification

```bash
npm run type-check && npm run lint && npm run build
```

---

## Phase 4.5: Page Implementation

### Pages to Build

| Page | File | Spec |
|------|------|------|
| Home | `app/page.tsx` | [home-page.md](../components/pages/home-page.md) |
| Chat | `app/chat/page.tsx` + `client.tsx` | [chat-page.md](../components/pages/chat-page.md) |
| Dashboard | `app/dashboard/page.tsx` | [dashboard-page.md](../components/pages/dashboard-page.md) |
| History | `app/history/page.tsx` + `client.tsx` | [history-page.md](../components/pages/history-page.md) |

### Supporting Files

| File | Purpose |
|------|---------|
| `app/chat/loading.tsx` | Chat loading skeleton |
| `app/chat/error.tsx` | Chat error boundary |
| `app/dashboard/loading.tsx` | Dashboard loading skeleton |
| `app/dashboard/error.tsx` | Dashboard error boundary |
| `app/history/loading.tsx` | History loading skeleton |

### Implementation Order

1. **Home page** - Landing or redirect
2. **Chat page** - Full three-column layout
3. **Dashboard page** - Analytics with charts
4. **History page** - Session browser

### Required Dependencies

```bash
# nuqs already in Phase 1
npm install nuqs
```

### Verification

```bash
npm run type-check && npm run lint && npm run build
npm run dev  # Manual verification of all pages
```

---

## Component Dependency Graph

```
┌─────────────────────────────────────────────────────────────────┐
│                         PHASE 4.5: PAGES                         │
│  ┌─────────┐  ┌─────────┐  ┌───────────┐  ┌─────────────────┐  │
│  │  Home   │  │  Chat   │  │ Dashboard │  │     History     │  │
│  └─────────┘  └────┬────┘  └─────┬─────┘  └────────┬────────┘  │
└────────────────────┼─────────────┼─────────────────┼────────────┘
                     │             │                 │
┌────────────────────┼─────────────┼─────────────────┼────────────┐
│  PHASE 4.2-4.4     │             │                 │            │
│  ┌─────────────────▼─────────────┼─────────────────┘            │
│  │                               │                              │
│  │  ┌────────────┐  ┌────────────┴────┐  ┌────────────────┐    │
│  │  │ ChatWindow │  │  ManualToolPanel│  │ SessionsChart  │    │
│  │  └─────┬──────┘  └────────┬────────┘  └────────────────┘    │
│  │        │                  │                                  │
│  │  ┌─────┴──────┐  ┌────────┴─────┐  ┌────────────────────┐   │
│  │  │MessageBubble│  │  ToolCard   │  │   SummaryCards     │   │
│  │  │ToolExecCard │  │ OSILadderViz│  │  ToolStatsTable    │   │
│  │  └────────────┘  └──────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────┐
│  PHASE 4.1: LAYOUT          │                                   │
│  ┌──────────┐  ┌────────────┴───────┐  ┌─────────────────────┐ │
│  │  Header  │  │      Sidebar       │  │   MobileSidebar     │ │
│  └──────────┘  └────────────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────┐
│  PHASE 3: HOOKS             │                                   │
│  ┌──────────────┐  ┌────────┴────────┐                         │
│  │ useWebSocket │  │    useChat      │                         │
│  └──────────────┘  └─────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## File Structure After Phase 4

```
frontend/techtime/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                    # Home (redirect or landing)
│   ├── chat/
│   │   ├── page.tsx                # Server component
│   │   ├── client.tsx              # Client component
│   │   ├── loading.tsx
│   │   └── error.tsx
│   ├── dashboard/
│   │   ├── page.tsx
│   │   ├── loading.tsx
│   │   └── error.tsx
│   └── history/
│       ├── page.tsx
│       ├── client.tsx
│       └── loading.tsx
├── components/
│   ├── layout/
│   │   ├── Header.tsx              # Updated
│   │   ├── Sidebar.tsx             # New
│   │   └── MobileSidebar.tsx       # New
│   ├── chat/
│   │   ├── ChatWindow.tsx          # New
│   │   ├── MessageBubble.tsx       # New
│   │   └── ToolExecutionCard.tsx   # New
│   ├── diagnostics/
│   │   ├── ToolCard.tsx            # New
│   │   ├── OSILadderViz.tsx        # New
│   │   └── ManualToolPanel.tsx     # New
│   ├── analytics/
│   │   ├── SummaryCards.tsx        # New
│   │   ├── SessionsChart.tsx       # New (includes Category, ToolUsage)
│   │   ├── ToolStatsTable.tsx      # New
│   │   └── DateRangePicker.tsx     # New
│   ├── ui/                         # shadcn components (existing)
│   └── theme-provider.tsx
├── hooks/
│   ├── index.ts                    # Updated with new exports
│   ├── use-websocket.ts            # Existing
│   ├── use-chat.ts                 # Existing
│   ├── use-osi-ladder.ts           # New
│   ├── use-manual-tool-panel.ts    # New
│   └── use-tool-execution.ts       # New
├── lib/
│   ├── utils.ts                    # Existing
│   ├── api.ts                      # Existing
│   └── websocket.ts                # Existing
└── types/
    └── index.ts                    # Existing
```

---

## Implementation Checklist

### Phase 4.1 Checklist

- [ ] Header updated with mobile menu dropdown
- [ ] Sidebar component created
- [ ] MobileSidebar (Sheet wrapper) created
- [ ] All layout tests passing
- [ ] `tsc --noEmit` passes
- [ ] `npm run lint` passes
- [ ] `npm run build` passes

### Phase 4.2 Checklist

- [ ] MessageBubble with markdown rendering
- [ ] useToolExecution hook created
- [ ] ToolExecutionCard with states
- [ ] ChatWindow with auto-scroll
- [ ] Empty state and suggestions working
- [ ] `tsc --noEmit` passes
- [ ] `npm run lint` passes
- [ ] `npm run build` passes

### Phase 4.3 Checklist

- [ ] useOSILadder hook created
- [ ] OSILadderViz with all states
- [ ] ToolCard with parameters
- [ ] useManualToolPanel hook created
- [ ] ManualToolPanel with categories
- [ ] `tsc --noEmit` passes
- [ ] `npm run lint` passes
- [ ] `npm run build` passes

### Phase 4.4 Checklist

- [ ] SummaryCards with metrics
- [ ] SessionsChart (line/area)
- [ ] CategoryChart (pie)
- [ ] ToolUsageChart (bar)
- [ ] ToolStatsTable with sorting
- [ ] DateRangePicker component
- [ ] `tsc --noEmit` passes
- [ ] `npm run lint` passes
- [ ] `npm run build` passes

### Phase 4.5 Checklist

- [ ] Home page (redirect or landing)
- [ ] Chat page with three-column layout
- [ ] Dashboard page with all charts
- [ ] History page with filters
- [ ] All loading states
- [ ] All error boundaries
- [ ] Responsive design verified
- [ ] `tsc --noEmit` passes
- [ ] `npm run lint` passes
- [ ] `npm run build` passes
- [ ] Manual testing complete

---

## Verification Commands

After each sub-phase:

```bash
# Type checking
npx tsc --noEmit

# Linting
npm run lint

# Build
npm run build

# Development server
npm run dev
```

---

## Notes

1. **Headless Pattern**: Components like OSILadderViz, ManualToolPanel, and ToolExecutionCard use headless hooks for state management, allowing custom UI implementations.

2. **Server/Client Split**: Pages use the pattern of a server component (`page.tsx`) fetching data and a client component (`client.tsx`) handling interactivity.

3. **Incremental Delivery**: Each sub-phase produces working functionality that can be tested independently.

4. **Spec Compliance**: Each component must match its specification document in `doccs/components/`.

---

## Related Documents

- [PHASE-1-FOUNDATION.md](./PHASE-1-FOUNDATION.md)
- [PHASE-2-LIBRARIES.md](./PHASE-2-LIBRARIES.md)
- [PHASE-3-HOOKS.md](./PHASE-3-HOOKS.md)
- [VERIFICATION_CHECKLIST.md](../VERIFICATION_CHECKLIST.md)

