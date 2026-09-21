import type { ButtonHTMLAttributes } from 'react'

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string
  bordered?: boolean
  size?: 'sm' | 'md'
}

export function IconButton({
  label,
  bordered = false,
  size = 'md',
  className = '',
  children,
  ...rest
}: IconButtonProps) {
  const cls = [
    'icon-btn',
    bordered ? 'icon-btn--bordered' : '',
    size === 'sm' ? 'icon-btn--sm' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')
  return (
    <button className={cls} aria-label={label} title={label} {...rest}>
      {children}
    </button>
  )
}
