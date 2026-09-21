export interface ProgressBarProps {
  value: number
  max?: number
  tone?: 'brand' | 'ink'
  label?: string
}

export function ProgressBar({ value, max = 100, tone = 'brand', label }: ProgressBarProps) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div
      className="progress"
      role="progressbar"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
    >
      <div
        className={tone === 'ink' ? 'progress__fill progress__fill--ink' : 'progress__fill'}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}
