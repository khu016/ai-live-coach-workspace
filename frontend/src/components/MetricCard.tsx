export interface MetricCardProps {
  label: string
  value: string | number
  unit?: string
  hint?: string
  brand?: boolean
}

export function MetricCard({ label, value, unit, hint, brand = false }: MetricCardProps) {
  return (
    <div className="metric-card">
      <span className="metric-card__label">{label}</span>
      <span className={brand ? 'metric-card__value metric-card__value--brand' : 'metric-card__value'}>
        {value}
        {unit ? <span className="unit">{unit}</span> : null}
      </span>
      {hint ? <span className="metric-card__hint">{hint}</span> : null}
    </div>
  )
}
