import type { ReactNode } from 'react'

export type StatusTone = 'neutral' | 'brand' | 'success' | 'warning' | 'danger' | 'ink'

export interface StatusTagProps {
  tone?: StatusTone
  children: ReactNode
}

export function StatusTag({ tone = 'neutral', children }: StatusTagProps) {
  return <span className={`status-tag status-tag--${tone}`}>{children}</span>
}
