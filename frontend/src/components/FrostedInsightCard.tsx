import type { ReactNode } from 'react'
import { Sparkles } from 'lucide-react'

export interface FrostedInsightCardProps {
  title?: string
  children: ReactNode
}

export function FrostedInsightCard({ title, children }: FrostedInsightCardProps) {
  return (
    <div className="frosted frosted-insight">
      {title && (
        <div className="frosted-insight__title">
          <Sparkles size={14} aria-hidden />
          <span>{title}</span>
        </div>
      )}
      <div className="frosted-insight__body">{children}</div>
    </div>
  )
}
