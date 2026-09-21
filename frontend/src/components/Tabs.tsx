export interface TabOption {
  key: string
  label: string
}

export interface TabsProps {
  options: TabOption[]
  value: string
  onChange: (key: string) => void
  ariaLabel?: string
}

export function Tabs({ options, value, onChange, ariaLabel }: TabsProps) {
  return (
    <div className="tabs" role="tablist" aria-label={ariaLabel}>
      {options.map((o) => (
        <button
          key={o.key}
          role="tab"
          aria-selected={value === o.key}
          className={value === o.key ? 'tabs__item tabs__item--active' : 'tabs__item'}
          onClick={() => onChange(o.key)}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
