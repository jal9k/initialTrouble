# Utility Functions

This document specifies the utility functions used throughout the Network Diagnostics frontend.

## File Location

```
frontend/
  lib/
    utils.ts        # Utility functions
```

---

## Overview

The utils module provides common helper functions for:
- Class name merging (Tailwind)
- Date/time formatting
- String manipulation
- Type helpers

---

## Class Name Utilities

### cn (Class Name Merge)

```typescript
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Merge class names with Tailwind CSS conflict resolution
 * 
 * @example
 * cn('px-2 py-1', 'px-4') // => 'py-1 px-4'
 * cn('text-red-500', condition && 'text-blue-500')
 */
function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}
```

### Dependencies

```json
{
  "dependencies": {
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0"
  }
}
```

---

## Date/Time Utilities

### formatDate

```typescript
/**
 * Format a date for display
 * 
 * @example
 * formatDate(new Date()) // => 'Dec 21, 2025'
 * formatDate(new Date(), 'time') // => '2:30 PM'
 */
function formatDate(
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
```

### formatRelativeTime

```typescript
/**
 * Format a date as relative time (e.g., "5 minutes ago")
 */
function formatRelativeTime(date: Date): string {
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
```

### formatDuration

```typescript
/**
 * Format a duration in milliseconds
 * 
 * @example
 * formatDuration(5000) // => '5s'
 * formatDuration(125000) // => '2m 5s'
 */
function formatDuration(ms: number): string {
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
```

---

## String Utilities

### truncate

```typescript
/**
 * Truncate a string to a maximum length
 * 
 * @example
 * truncate('Hello World', 5) // => 'Hello...'
 */
function truncate(str: string, maxLength: number, suffix = '...'): string {
  if (str.length <= maxLength) return str
  return str.slice(0, maxLength - suffix.length) + suffix
}
```

### capitalize

```typescript
/**
 * Capitalize the first letter of a string
 * 
 * @example
 * capitalize('hello') // => 'Hello'
 */
function capitalize(str: string): string {
  if (!str) return str
  return str.charAt(0).toUpperCase() + str.slice(1)
}
```

### slugify

```typescript
/**
 * Convert a string to a URL-friendly slug
 * 
 * @example
 * slugify('Hello World!') // => 'hello-world'
 */
function slugify(str: string): string {
  return str
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
}
```

---

## Number Utilities

### formatNumber

```typescript
/**
 * Format a number for display
 * 
 * @example
 * formatNumber(1234567) // => '1,234,567'
 * formatNumber(0.856, 'percent') // => '85.6%'
 * formatNumber(1234.56, 'currency') // => '$1,234.56'
 */
function formatNumber(
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
```

### clamp

```typescript
/**
 * Clamp a number between min and max
 * 
 * @example
 * clamp(5, 0, 10) // => 5
 * clamp(-5, 0, 10) // => 0
 * clamp(15, 0, 10) // => 10
 */
function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}
```

---

## ID Utilities

### generateId

```typescript
/**
 * Generate a unique ID
 * 
 * @example
 * generateId() // => 'abc123xyz'
 * generateId('msg') // => 'msg_abc123xyz'
 */
function generateId(prefix?: string): string {
  const id = Math.random().toString(36).substring(2, 11)
  return prefix ? `${prefix}_${id}` : id
}
```

---

## Async Utilities

### sleep

```typescript
/**
 * Wait for a specified duration
 * 
 * @example
 * await sleep(1000) // Wait 1 second
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}
```

### debounce

```typescript
/**
 * Debounce a function
 * 
 * @example
 * const debouncedSearch = debounce(search, 300)
 */
function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout | null = null
  
  return (...args: Parameters<T>) => {
    if (timeoutId) clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), delay)
  }
}
```

### throttle

```typescript
/**
 * Throttle a function
 * 
 * @example
 * const throttledScroll = throttle(handleScroll, 100)
 */
function throttle<T extends (...args: unknown[]) => unknown>(
  fn: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false
  
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      fn(...args)
      inThrottle = true
      setTimeout(() => { inThrottle = false }, limit)
    }
  }
}
```

---

## Validation Utilities

### isValidUrl

```typescript
/**
 * Check if a string is a valid URL
 */
function isValidUrl(str: string): boolean {
  try {
    new URL(str)
    return true
  } catch {
    return false
  }
}
```

### isEmpty

```typescript
/**
 * Check if a value is empty
 */
function isEmpty(value: unknown): boolean {
  if (value === null || value === undefined) return true
  if (typeof value === 'string') return value.trim().length === 0
  if (Array.isArray(value)) return value.length === 0
  if (typeof value === 'object') return Object.keys(value).length === 0
  return false
}
```

---

## Export Pattern

```typescript
// lib/utils.ts

export {
  // Class names
  cn,
  
  // Date/time
  formatDate,
  formatRelativeTime,
  formatDuration,
  
  // Strings
  truncate,
  capitalize,
  slugify,
  
  // Numbers
  formatNumber,
  clamp,
  
  // IDs
  generateId,
  
  // Async
  sleep,
  debounce,
  throttle,
  
  // Validation
  isValidUrl,
  isEmpty
}
```

---

## Usage Examples

### Class Name Merging

```typescript
import { cn } from '@/lib/utils'

function Button({ variant, className }) {
  return (
    <button
      className={cn(
        'px-4 py-2 rounded font-medium',
        variant === 'primary' && 'bg-primary text-primary-foreground',
        variant === 'outline' && 'border border-input bg-background',
        className
      )}
    >
      Click me
    </button>
  )
}
```

### Formatting

```typescript
import { formatDate, formatDuration, formatNumber } from '@/lib/utils'

function SessionCard({ session }) {
  return (
    <div>
      <p>{formatDate(session.startTime, 'relative')}</p>
      <p>Duration: {formatDuration(session.duration)}</p>
      <p>Resolution Rate: {formatNumber(session.resolutionRate, 'percent')}</p>
    </div>
  )
}
```

---

## Test Specifications

### cn Tests

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| Basic merge | `cn('a', 'b')` | `'a b'` |
| Conditional | `cn('a', false && 'b')` | `'a'` |
| Tailwind conflict | `cn('px-2', 'px-4')` | `'px-4'` |
| Undefined handling | `cn('a', undefined)` | `'a'` |

### Date Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| formatDate with 'date' | Returns formatted date |
| formatDate with 'time' | Returns formatted time |
| formatRelativeTime recent | Returns 'just now' |
| formatRelativeTime hours | Returns 'X hours ago' |
| formatDuration ms | Returns 'Xms' |
| formatDuration minutes | Returns 'Xm Ys' |

### String Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| truncate short string | Returns unchanged |
| truncate long string | Returns with suffix |
| capitalize empty | Returns empty |
| slugify with special chars | Returns clean slug |

### Number Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| formatNumber default | Returns with commas |
| formatNumber percent | Returns percentage |
| formatNumber currency | Returns with $ |
| clamp within range | Returns value |
| clamp below min | Returns min |

### Async Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| sleep resolves after delay | Promise resolves |
| debounce only calls once | Function called once after delay |
| throttle limits calls | Function called at most once per limit |

---

## Lint/Build Verification

- [ ] All functions properly typed
- [ ] No any types used
- [ ] Pure functions (no side effects)
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All unit tests pass
- [ ] 100% test coverage

---

## Related Documents

- [interfaces.md](../types/interfaces.md) - Type definitions
- [ChatWindow.md](../components/chat/ChatWindow.md) - Uses cn for styling

