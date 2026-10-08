import Lenis from 'lenis'
import { useEffect, type ReactNode } from 'react'

export function SmoothScrollProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)')
    let lenis: Lenis | undefined
    let frameId = 0

    const animate = (time: number) => {
      lenis?.raf(time)
      if (lenis) frameId = window.requestAnimationFrame(animate)
    }

    const stop = () => {
      window.cancelAnimationFrame(frameId)
      lenis?.destroy()
      lenis = undefined
    }

    const updatePreference = () => {
      stop()
      if (preference.matches) return
      lenis = new Lenis({ lerp: 0.09, smoothWheel: true })
      frameId = window.requestAnimationFrame(animate)
    }

    updatePreference()
    preference.addEventListener('change', updatePreference)
    return () => {
      preference.removeEventListener('change', updatePreference)
      stop()
    }
  }, [])

  return children
}
