import { useCallback, useEffect, useRef, useState } from 'react'

type SplashScreenProps = {
  onComplete: () => void
  onExitStart: () => void
}

const DISPLAY_MS = 1800
const EXIT_MS = 700

export function SplashScreen({ onComplete, onExitStart }: SplashScreenProps) {
  const [leaving, setLeaving] = useState(false)
  const exitStarted = useRef(false)
  const exitTimer = useRef<number>()

  const leave = useCallback(() => {
    if (exitStarted.current) return
    exitStarted.current = true
    onExitStart()
    setLeaving(true)
    exitTimer.current = window.setTimeout(onComplete, EXIT_MS)
  }, [onComplete, onExitStart])

  useEffect(() => {
    const displayTimer = window.setTimeout(leave, DISPLAY_MS)

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Enter' || event.key === ' ' || event.key === 'Escape') {
        event.preventDefault()
        leave()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.clearTimeout(displayTimer)
      if (exitTimer.current) window.clearTimeout(exitTimer.current)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [leave])

  return (
    <button
      className={`splash-screen${leaving ? ' splash-screen--leaving' : ''}`}
      type="button"
      onClick={leave}
      aria-label="NIVI 正在准备训练环境，点击跳过"
    >
      <span className="splash-screen__halo" aria-hidden />
      <span className="splash-screen__brand">
        <span className="splash-screen__mark">
          <img src="/assets/ai-coach-logo.png" alt="" />
        </span>
        <span className="splash-screen__name" aria-label="NIVI">
          <i>N</i><i>I</i><i>V</i><i>I</i>
        </span>
        <span className="splash-screen__tagline">开播前，先练一次</span>
      </span>
      <span className="splash-screen__skip">点击跳过</span>
    </button>
  )
}
