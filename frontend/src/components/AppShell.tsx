import type { ReactNode } from 'react'
import { TopNavigation } from './TopNavigation'
import { ToastRegion } from './Toast'
import { AnalyticsTracker } from './AnalyticsTracker'
import { CursorGlowBackdrop } from './CursorGlowBackdrop'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <CursorGlowBackdrop />
      <AnalyticsTracker />
      <TopNavigation />
      <main className="app-shell__main">{children}</main>
      <ToastRegion />
    </div>
  )
}
