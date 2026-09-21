import type { ReactNode } from 'react'
import { TopNavigation } from './TopNavigation'
import { ToastRegion } from './Toast'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <TopNavigation />
      <main className="app-shell__main">{children}</main>
      <ToastRegion />
    </div>
  )
}
