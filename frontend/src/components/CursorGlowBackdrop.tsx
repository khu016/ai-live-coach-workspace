import { useEffect, useRef } from 'react'

export function CursorGlowBackdrop() {
  const layerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const layer = layerRef.current
    if (!layer) return

    const precisePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!precisePointer || reducedMotion) {
      layer.classList.add('is-static')
      return
    }

    const rect = layer.getBoundingClientRect()
    const target = { x: rect.width * 0.68, y: rect.height * 0.32 }
    const glow = { ...target }
    const trail = { x: rect.width * 0.58, y: rect.height * 0.42 }
    let frame = 0

    const onPointerMove = (event: PointerEvent) => {
      const bounds = layer.getBoundingClientRect()
      target.x = Math.min(bounds.width, Math.max(0, event.clientX - bounds.left))
      target.y = Math.min(bounds.height, Math.max(0, event.clientY - bounds.top))
      layer.classList.add('is-active')
    }

    const onPointerLeave = () => layer.classList.remove('is-active')

    const render = () => {
      glow.x += (target.x - glow.x) * 0.085
      glow.y += (target.y - glow.y) * 0.085
      trail.x += (glow.x - trail.x) * 0.034
      trail.y += (glow.y - trail.y) * 0.034
      layer.style.setProperty('--cursor-glow-x', `${glow.x}px`)
      layer.style.setProperty('--cursor-glow-y', `${glow.y}px`)
      layer.style.setProperty('--cursor-trail-x', `${trail.x}px`)
      layer.style.setProperty('--cursor-trail-y', `${trail.y}px`)
      frame = requestAnimationFrame(render)
    }

    layer.parentElement?.addEventListener('pointermove', onPointerMove, { passive: true })
    layer.parentElement?.addEventListener('pointerleave', onPointerLeave)
    frame = requestAnimationFrame(render)
    return () => {
      layer.parentElement?.removeEventListener('pointermove', onPointerMove)
      layer.parentElement?.removeEventListener('pointerleave', onPointerLeave)
      cancelAnimationFrame(frame)
    }
  }, [])

  return <div className="cursor-glow-backdrop" ref={layerRef} aria-hidden="true" />
}
