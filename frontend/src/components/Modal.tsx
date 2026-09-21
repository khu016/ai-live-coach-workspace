import { useEffect, type ReactNode } from 'react'
import { X } from 'lucide-react'
import { IconButton } from './IconButton'

export interface ModalProps {
  open: boolean
  title?: string
  onClose: () => void
  children?: ReactNode
  footer?: ReactNode
}

export function Modal({ open, title, onClose, children, footer }: ModalProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal__header">
          <h3 className="text-lg semibold">{title}</h3>
          <IconButton label="关闭" size="sm" onClick={onClose}>
            <X size={16} />
          </IconButton>
        </div>
        {children ? <div className="modal__body">{children}</div> : null}
        {footer ? <div className="modal__footer">{footer}</div> : null}
      </div>
    </div>
  )
}
