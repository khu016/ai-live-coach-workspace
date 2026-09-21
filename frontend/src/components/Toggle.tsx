export interface ToggleProps {
  checked: boolean
  onChange: (value: boolean) => void
  label: string
  id?: string
}

export function Toggle({ checked, onChange, label, id }: ToggleProps) {
  return (
    <label className="toggle">
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        aria-label={label}
      />
      <span className="toggle__track" />
      <span className="toggle__thumb" />
    </label>
  )
}
