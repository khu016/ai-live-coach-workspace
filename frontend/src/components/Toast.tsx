import { CheckCircle2, AlertTriangle, Info, X } from 'lucide-react'
import { useApp } from '../store/AppContext'

export function ToastRegion() {
  const { toasts, dismissToast } = useApp()
  if (toasts.length === 0) return null

  return (
    <div className="toast-region" aria-live="polite">
      {toasts.map((t) => {
        const Icon = t.kind === 'success' ? CheckCircle2 : t.kind === 'error' ? AlertTriangle : Info
        return (
          <div key={t.id} className={`toast toast--${t.kind}`} role="status">
            <Icon size={16} aria-hidden />
            <span className="toast__msg">{t.message}</span>
            <button className="toast__close" onClick={() => dismissToast(t.id)} aria-label="关闭提示">
              <X size={14} />
            </button>
          </div>
        )
      })}
    </div>
  )
}
