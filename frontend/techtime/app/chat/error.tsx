'use client'

import { Button } from '@/components/ui/button'
import { RefreshCw, AlertCircle } from 'lucide-react'

export default function ChatError({
  error,
  reset
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center h-[calc(100vh-56px)] p-4">
      <div className="flex items-center gap-2 text-destructive mb-4">
        <AlertCircle className="h-8 w-8" />
        <h2 className="text-xl font-semibold">Something went wrong</h2>
      </div>
      <p className="text-muted-foreground mb-6 text-center max-w-md">
        {error.message || 'An unexpected error occurred while loading the chat.'}
      </p>
      <Button onClick={reset} variant="default">
        <RefreshCw className="h-4 w-4 mr-2" />
        Try again
      </Button>
    </div>
  )
}

