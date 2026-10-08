import { motion, useReducedMotion, useScroll } from 'framer-motion'

export function ScrollProgress() {
  const { scrollYProgress } = useScroll()
  const reduceMotion = useReducedMotion()

  if (reduceMotion) return null

  return (
    <motion.div
      aria-hidden="true"
      className="scroll-progress"
      style={{ scaleX: scrollYProgress }}
    />
  )
}
