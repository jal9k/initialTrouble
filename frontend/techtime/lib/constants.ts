// lib/constants.ts
// Centralized configuration constants for the application

// ============================================================================
// WebSocket Configuration
// ============================================================================

/** Interval between reconnection attempts in milliseconds */
export const WS_RECONNECT_INTERVAL = 3000

/** Maximum number of reconnection attempts before giving up */
export const WS_MAX_RECONNECT_ATTEMPTS = 5

// ============================================================================
// PyWebView Configuration
// ============================================================================

/** Timeout for waiting for PyWebView API to become available (ms) */
export const PYWEBVIEW_TIMEOUT = 5000

// ============================================================================
// Session/Chat Configuration
// ============================================================================

/** Default page size for session list queries */
export const SESSION_PAGE_SIZE = 20

/** Delay before refetching sessions after first message (ms) */
export const SESSION_REFETCH_DELAY = 1000

/** LocalStorage key for persisting chat state */
export const CHAT_STORAGE_KEY = 'techtime_chat'

// ============================================================================
// UI Configuration
// ============================================================================

/** Scroll threshold for showing "scroll to bottom" button (px) */
export const SCROLL_THRESHOLD = 100

/** Sidebar width when expanded (Tailwind class) */
export const SIDEBAR_WIDTH = 'w-72'

/** Sidebar width when collapsed (Tailwind class) */
export const SIDEBAR_COLLAPSED_WIDTH = 'w-16'

/** Right panel width when expanded (Tailwind class) */
export const RIGHT_PANEL_WIDTH = 'w-80'

/** Right panel width when collapsed (Tailwind class) */
export const RIGHT_PANEL_COLLAPSED_WIDTH = 'w-16'

/** Default chart height in pixels */
export const CHART_HEIGHT = 300

/** Pie chart height in pixels */
export const PIE_CHART_HEIGHT = 250

// ============================================================================
// Business Logic Thresholds
// ============================================================================

/** Success rate threshold for "High" badge (90%) */
export const SUCCESS_RATE_HIGH_THRESHOLD = 0.9

/** Success rate threshold for "Medium" badge (70%) */
export const SUCCESS_RATE_MEDIUM_THRESHOLD = 0.7

// ============================================================================
// Date Range Defaults
// ============================================================================

/** Default date range for analytics (30 days in milliseconds) */
export const DEFAULT_DATE_RANGE_MS = 30 * 24 * 60 * 60 * 1000

// ============================================================================
// Animation Durations
// ============================================================================

/** Duration for copy feedback timeout (ms) */
export const COPY_FEEDBACK_DURATION = 2000

/** Simulated loading duration for UI transitions (ms) */
export const LOADING_SIMULATION_DURATION = 500
