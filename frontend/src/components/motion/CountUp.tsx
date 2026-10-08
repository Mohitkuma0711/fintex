import { useEffect, useState } from 'react'
import { useReducedMotion } from 'framer-motion'
import { formatINR } from '../../lib/formatters'

interface CountUpProps {
  value: number
  duration?: number
  className?: string
}

export function CountUp({ value, duration = 1400, className }: CountUpProps) {
  const reduceMotion = useReducedMotion()
  const [displayValue, setDisplayValue] = useState(0)

  useEffect(() => {
    if (reduceMotion) return

    let frameId = 0
    const startTime = performance.now()
    const animate = (now: number) => {
      const progress = Math.min((now - startTime) / duration, 1)
      const eased = 1 - (1 - progress) ** 4
      setDisplayValue(Math.round(value * eased))
      if (progress < 1) frameId = window.requestAnimationFrame(animate)
    }

    frameId = window.requestAnimationFrame(animate)
    return () => window.cancelAnimationFrame(frameId)
  }, [duration, reduceMotion, value])

  return <span className={className}>{formatINR(reduceMotion ? value : displayValue)}</span>
}
