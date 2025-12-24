# Home Page

This document specifies the Home page (`/`), the application entry point.

## File Location

```
frontend/
  app/
    page.tsx
```

---

## Overview

The Home page serves as the entry point and immediately redirects users to the Chat page. This can be enhanced later to show a landing page or dashboard summary.

---

## Current Behavior

**Redirect to `/chat`**

The simplest implementation redirects users to the main chat interface:

```typescript
// app/page.tsx

import { redirect } from 'next/navigation'

export default function HomePage() {
  redirect('/chat')
}
```

---

## Alternative: Landing Page

For a more polished experience, display a landing page with navigation options:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Header                                                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│                                                                                 │
│                    ┌─────────────────────────────────────┐                     │
│                    │                                     │                     │
│                    │     TechTime             │                     │
│                    │     AI-Powered Troubleshooting      │                     │
│                    │                                     │                     │
│                    │     [Start New Session]             │                     │
│                    │                                     │                     │
│                    └─────────────────────────────────────┘                     │
│                                                                                 │
│                                                                                 │
│     ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│     │                 │  │                 │  │                 │             │
│     │  💬 Chat        │  │  📊 Dashboard   │  │  📜 History     │             │
│     │                 │  │                 │  │                 │             │
│     │  Start a new    │  │  View analytics │  │  Browse past    │             │
│     │  diagnostic     │  │  and metrics    │  │  sessions       │             │
│     │  session        │  │                 │  │                 │             │
│     │                 │  │                 │  │                 │             │
│     └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                                 │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Landing Page Implementation

```typescript
// app/page.tsx

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { MessageSquare, BarChart3, History, ArrowRight } from 'lucide-react'

export const metadata = {
  title: 'TechTime',
  description: 'AI-powered network troubleshooting assistant'
}

const features = [
  {
    title: 'Chat',
    description: 'Start a new diagnostic session with our AI assistant',
    icon: MessageSquare,
    href: '/chat'
  },
  {
    title: 'Dashboard',
    description: 'View analytics, metrics, and tool performance',
    icon: BarChart3,
    href: '/dashboard'
  },
  {
    title: 'History',
    description: 'Browse and continue past diagnostic sessions',
    icon: History,
    href: '/history'
  }
]

export default function HomePage() {
  return (
    <div className="container py-12">
      {/* Hero Section */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold tracking-tight mb-4">
          TechTime
        </h1>
        <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
          AI-powered troubleshooting for your network issues. 
          Describe your problem and get step-by-step diagnostic assistance.
        </p>
        <Link href="/chat">
          <Button size="lg">
            Start New Session
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </Link>
      </div>

      {/* Feature Cards */}
      <div className="grid gap-6 md:grid-cols-3 max-w-4xl mx-auto">
        {features.map((feature) => (
          <Link key={feature.href} href={feature.href}>
            <Card className="h-full hover:border-primary/50 transition-colors cursor-pointer">
              <CardHeader>
                <feature.icon className="h-8 w-8 text-primary mb-2" />
                <CardTitle>{feature.title}</CardTitle>
                <CardDescription>{feature.description}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>

      {/* Quick Stats (optional) */}
      <div className="mt-16 text-center">
        <p className="text-sm text-muted-foreground">
          Powered by AI diagnostics across 5 network layers
        </p>
      </div>
    </div>
  )
}
```

---

## Recommended Approach

For the initial implementation, use the **redirect approach**. This gets users into the app quickly. The landing page can be added later for marketing/onboarding purposes.

```typescript
// Simple redirect (recommended for v1)
import { redirect } from 'next/navigation'

export default function HomePage() {
  redirect('/chat')
}
```

---

## Loading State

```typescript
// app/loading.tsx (root loading)
import { Loader2 } from 'lucide-react'

export default function RootLoading() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  )
}
```

---

## Test Specifications

### Redirect Version

| Test Case | Expected Behavior |
|-----------|-------------------|
| Visit `/` | Redirects to `/chat` |
| No flash | Redirect is instant (server-side) |

### Landing Page Version

| Test Case | Expected Behavior |
|-----------|-------------------|
| Page renders | Hero and cards visible |
| CTA button works | Navigates to `/chat` |
| Feature cards link | Each navigates correctly |
| Responsive layout | Cards stack on mobile |

---

## Lint/Build Verification

- [ ] Page renders or redirects
- [ ] No hydration errors
- [ ] Links work correctly
- [ ] `tsc --noEmit` passes
- [ ] ESLint passes
- [ ] All tests pass

---

## Related Documents

- [chat-page.md](./chat-page.md) - Primary destination
- [dashboard-page.md](./dashboard-page.md) - Analytics
- [history-page.md](./history-page.md) - Session history
- [Header.md](../layout/Header.md) - Navigation header

