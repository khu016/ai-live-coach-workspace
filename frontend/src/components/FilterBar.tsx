export interface FilterBarProps {
  options: string[]
  value: string
  onChange: (value: string) => void
  label?: string
}

export function FilterBar({ options, value, onChange, label }: FilterBarProps) {
  return (
    <div className="filter-bar" role="group" aria-label={label}>
      {options.map((o) => (
        <button
          key={o}
          className={value === o ? 'filter-chip filter-chip--active' : 'filter-chip'}
          onClick={() => onChange(o)}
        >
          {o}
        </button>
      ))}
    </div>
  )
}
