# Header Component

This document specifies the Header component for the TechTime application.

## File Location

```
frontend/
  components/
    layout/
      Header.tsx
```

---

## Overview

The Header component provides:
- Application branding/logo
- Main navigation links
- Theme toggle (dark/light mode)
- Connection status indicator
- User actions (if authentication added later)

---

## Props Interface

```typescript
interface HeaderProps {
  /** Additional CSS classes */
  className?: string
}
```

---

## Component Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Header                                                                 │
│  ┌──────────────┬────────────────────────────────┬───────────────────┐ │
│  │    Logo      │         Navigation             │   Actions         │ │
│  │              │  [Chat] [Dashboard] [History]  │ [Theme] [Status]  │ │
│  └──────────────┴────────────────────────────────┴───────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component States

| State | Description | Visual |
|-------|-------------|--------|
| Default | Normal navigation | Standard styling |
| Active Link | Current page highlighted | Bold, underlined, or accented |
| Loading | Page transition | Subtle loading indicator |

---

## Behaviors

### Navigation
- Links use Next.js `Link` component for client-side navigation
- Active link highlighted based on current route
- Mobile: collapses to hamburger menu

### Theme Toggle
- Toggles between light and dark mode
- Persists preference to localStorage
- Uses `next-themes` for SSR-safe theming

### Connection Status
- Shows WebSocket connection state
- Green dot when connected
- Yellow pulsing dot when reconnecting
- Red dot when disconnected

---

## shadcn/ui Dependencies

| Component | Usage |
|-----------|-------|
| `Button` | Theme toggle, mobile menu |
| `NavigationMenu` | Main navigation links |
| `DropdownMenu` | Mobile menu, user menu |
| `Separator` | Visual dividers |

---

## Styling Guidelines

### Layout
```css
/* Sticky header */
.header {
  @apply sticky top-0 z-50 w-full;
  @apply border-b bg-background/95 backdrop-blur;
  @apply supports-[backdrop-filter]:bg-background/60;
}

/* Container */
.header-container {
  @apply container flex h-14 items-center;
}
```

### Navigation Links
```css
.nav-link {
  @apply text-sm font-medium transition-colors;
  @apply hover:text-primary;
}

.nav-link-active {
  @apply text-primary;
}

.nav-link-inactive {
  @apply text-muted-foreground;
}
```

### Responsive Behavior
```css
/* Desktop navigation */
.nav-desktop {
  @apply hidden md:flex gap-6;
}

/* Mobile navigation */
.nav-mobile {
  @apply md:hidden;
}
```

---

## Implementation

```typescript
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useTheme } from 'next-themes'
import { Moon, Sun, Menu, Wifi, WifiOff } from 'lucide-react'
import { useWebSocket } from '@/hooks/use-websocket'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'

const navItems = [
  { href: '/chat', label: 'Chat' },
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/history', label: 'History' }
]

export function Header({ className }: HeaderProps) {
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const { isConnected, isConnecting } = useWebSocket()

  return (
    <header className={cn(
      'sticky top-0 z-50 w-full border-b',
      'bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60',
      className
    )}>
      <div className="container flex h-14 items-center">
        {/* Logo */}
        <Link href="/" className="mr-6 flex items-center space-x-2">
          <span className="font-bold">TechTim(e)</span>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex gap-6">
          {navItems.map(item => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'text-sm font-medium transition-colors hover:text-primary',
                pathname === item.href
                  ? 'text-primary'
                  : 'text-muted-foreground'
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Actions */}
        <div className="flex items-center gap-2">
          {/* Connection Status */}
          <div className="flex items-center gap-1 text-sm">
            {isConnected ? (
              <Wifi className="h-4 w-4 text-green-500" />
            ) : isConnecting ? (
              <Wifi className="h-4 w-4 text-yellow-500 animate-pulse" />
            ) : (
              <WifiOff className="h-4 w-4 text-red-500" />
            )}
          </div>

          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            <span className="sr-only">Toggle theme</span>
          </Button>

          {/* Mobile Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild className="md:hidden">
              <Button variant="ghost" size="icon">
                <Menu className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {navItems.map(item => (
                <DropdownMenuItem key={item.href} asChild>
                  <Link href={item.href}>{item.label}</Link>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}
```

---

## Accessibility

| Feature | Implementation |
|---------|---------------|
| Skip link | Add "Skip to content" link for keyboard users |
| ARIA labels | All icon buttons have `aria-label` or `sr-only` text |
| Focus management | Visible focus rings on interactive elements |
| Keyboard nav | All links/buttons accessible via keyboard |

---

## Test Specifications

### Render Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Renders logo | Logo text visible |
| Renders nav links | All nav items present |
| Renders theme toggle | Button with icon visible |
| Renders connection status | Status indicator visible |

### Navigation Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Active link highlighted | Current page link styled differently |
| Links navigate correctly | Click triggers navigation |
| Mobile menu opens | Menu visible on trigger click |

### Theme Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Theme toggle works | Clicking switches theme |
| Icons swap on theme change | Sun/Moon icons toggle |

### Connection Status Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Connected shows green | Green indicator when connected |
| Connecting shows yellow | Yellow pulsing when connecting |
| Disconnected shows red | Red indicator when disconnected |

### Accessibility Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Keyboard navigation works | Tab through all interactive elements |
| Screen reader labels present | All buttons have accessible names |
| Focus visible | Focus rings on focus |

---

## Lint/Build Verification

- [ ] Component properly typed
- [ ] All imports resolved
- [ ] Responsive design works
- [ ] Dark mode works
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All tests pass

---

## Related Documents

- [Sidebar.md](./Sidebar.md) - Sidebar component
- [use-websocket.md](../../hooks/use-websocket.md) - Connection status
- [chat-page.md](../pages/chat-page.md) - Page using this header

