import { HistoryPageClient } from './client'

export const metadata = {
  title: 'History - TechTim(e)',
  description: 'Browse past support sessions'
}

/**
 * History page - statically exportable.
 *
 * For static export compatibility, we don't fetch data at build time.
 * The client component fetches sessions dynamically on mount.
 */
export default function HistoryPage() {
  return <HistoryPageClient />
}
