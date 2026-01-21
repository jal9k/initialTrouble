import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

// ============================================================================
// Class Name Utilities
// ============================================================================

/**
 * Merge class names with Tailwind CSS conflict resolution
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// ============================================================================
// Date/Time Utilities
// ============================================================================

/**
 * Format a date for display
 */
export function formatDate(
  date: Date | string,
  format: 'date' | 'time' | 'datetime' | 'relative' = 'date'
): string {
  const d = typeof date === 'string' ? new Date(date) : date

  switch (format) {
    case 'date':
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      })

    case 'time':
      return d.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit'
      })

    case 'datetime':
      return d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit'
      })

    case 'relative':
      return formatRelativeTime(d)
  }
}

/**
 * Format a date as relative time (e.g., "5 minutes ago")
 */
export function formatRelativeTime(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHour = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHour / 24)

  if (diffSec < 60) return 'just now'
  if (diffMin < 60) return `${diffMin} minute${diffMin === 1 ? '' : 's'} ago`
  if (diffHour < 24) return `${diffHour} hour${diffHour === 1 ? '' : 's'} ago`
  if (diffDay < 7) return `${diffDay} day${diffDay === 1 ? '' : 's'} ago`

  return formatDate(date, 'date')
}

/**
 * Format a duration in milliseconds
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`

  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (hours > 0) {
    const remainingMin = minutes % 60
    return `${hours}h ${remainingMin}m`
  }

  if (minutes > 0) {
    const remainingSec = seconds % 60
    return `${minutes}m ${remainingSec}s`
  }

  return `${seconds}s`
}

// ============================================================================
// String Utilities
// ============================================================================

/**
 * Truncate a string to a maximum length
 */
export function truncate(str: string, maxLength: number, suffix = '...'): string {
  if (str.length <= maxLength) return str
  // If suffix is longer than or equal to maxLength, just truncate without suffix
  if (suffix.length >= maxLength) return str.slice(0, maxLength)
  return str.slice(0, maxLength - suffix.length) + suffix
}

/**
 * Capitalize the first letter of a string
 */
export function capitalize(str: string): string {
  if (!str) return str
  return str.charAt(0).toUpperCase() + str.slice(1)
}

/**
 * Convert a string to a URL-friendly slug
 */
export function slugify(str: string): string {
  return str
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

// ============================================================================
// Number Utilities
// ============================================================================

/**
 * Format a number for display
 */
export function formatNumber(
  num: number,
  format: 'default' | 'percent' | 'currency' | 'compact' = 'default'
): string {
  switch (format) {
    case 'percent':
      return `${(num * 100).toFixed(1)}%`

    case 'currency':
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
      }).format(num)

    case 'compact':
      return new Intl.NumberFormat('en-US', {
        notation: 'compact',
        compactDisplay: 'short'
      }).format(num)

    default:
      return new Intl.NumberFormat('en-US').format(num)
  }
}

/**
 * Clamp a number between min and max
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

// ============================================================================
// ID Utilities
// ============================================================================

/**
 * Generate a unique ID
 */
export function generateId(prefix?: string): string {
  const id = Math.random().toString(36).substring(2, 11)
  return prefix ? `${prefix}_${id}` : id
}

// ============================================================================
// Async Utilities
// ============================================================================

/**
 * Wait for a specified duration
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Debounce a function
 */
export function debounce<T extends (...args: Parameters<T>) => ReturnType<T>>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout | null = null

  return (...args: Parameters<T>) => {
    if (timeoutId) clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), delay)
  }
}

/**
 * Throttle a function
 */
export function throttle<T extends (...args: Parameters<T>) => ReturnType<T>>(
  fn: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false

  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      fn(...args)
      inThrottle = true
      setTimeout(() => {
        inThrottle = false
      }, limit)
    }
  }
}

// ============================================================================
// Validation Utilities
// ============================================================================

/**
 * Check if a string is a valid URL
 */
export function isValidUrl(str: string): boolean {
  try {
    new URL(str)
    return true
  } catch {
    return false
  }
}

/**
 * Check if a value is empty
 */
export function isEmpty(value: unknown): boolean {
  if (value === null || value === undefined) return true
  if (typeof value === 'string') return value.trim().length === 0
  if (Array.isArray(value)) return value.length === 0
  if (typeof value === 'object') return Object.keys(value).length === 0
  return false
}
