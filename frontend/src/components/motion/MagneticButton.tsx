import { useReducedMotion } from 'framer-motion'
import { useRef, type ButtonHTMLAttributes, type PointerEvent } from 'react'

type MagneticButtonProps = ButtonHTMLAttributes<HTMLButtonElement>

export function MagneticButton({
  children,
  className = '',
  onPointerMove,
  onPointerLeave,
  ...props
}: MagneticButtonProps) {
  const buttonRef = useRef<HTMLButtonElement>(null)
  const reduceMotion = useReducedMotion()

  const moveButton = (event: PointerEvent<HTMLButtonElement>) => {
    onPointerMove?.(event)
    if (reduceMotion || event.pointerType !== 'mouse' || !buttonRef.current) return

    const bounds = buttonRef.current.getBoundingClientRect()
    const x = (event.clientX - bounds.left - bounds.width / 2) * 0.12
    const y = (event.clientY - bounds.top - bounds.height / 2) * 0.12
    buttonRef.current.style.transform = `translate3d(${x}px, ${y}px, 0)`
  }

  const resetButton = (event: PointerEvent<HTMLButtonElement>) => {
    onPointerLeave?.(event)
    if (buttonRef.current) buttonRef.current.style.transform = ''
  }

  return (
    <button
      ref={buttonRef}
      className={`magnetic-button ${className}`}
      onPointerMove={moveButton}
      onPointerLeave={resetButton}
      {...props}
    >
      {children}
    </button>
  )
}
