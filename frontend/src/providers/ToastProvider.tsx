import {
  useCallback,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { CircleCheck, CircleX, Info, X } from 'lucide-react'
import { ToastContext, type ToastMessage, type ToastTone } from './toast-context'

let nextToastId = 0

const toastIcons = {
  success: CircleCheck,
  error: CircleX,
  info: Info,
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((item) => item.id !== id))
  }, [])

  const toast = useCallback((message: string, tone: ToastTone = 'info') => {
    const id = ++nextToastId
    setToasts((current) => [...current.slice(-2), { id, message, tone }])
    window.setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== id))
    }, 5000)
  }, [])

  const value = useMemo(() => ({ toast }), [toast])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-region" aria-live="polite" aria-relevant="additions removals">
        <AnimatePresence initial={false}>
          {toasts.map((item) => {
            const Icon = toastIcons[item.tone]
            return (
              <motion.div
                className={`toast toast--${item.tone}`}
                key={item.id}
                role={item.tone === 'error' ? 'alert' : 'status'}
                initial={{ opacity: 0, y: 12, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.96 }}
                transition={{ duration: 0.2 }}
              >
                <Icon aria-hidden="true" size={19} />
                <span>{item.message}</span>
                <button
                  aria-label="Dismiss notification"
                  className="toast__close"
                  onClick={() => dismiss(item.id)}
                  type="button"
                >
                  <X aria-hidden="true" size={16} />
                </button>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}
