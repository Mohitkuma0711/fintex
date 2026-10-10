import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import * as Sentry from '@sentry/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import '@fontsource-variable/manrope'
import '@fontsource-variable/space-grotesk'
import './index.css'
import { App } from './app/App'
import { queryClient } from './lib/query-client'
import { SmoothScrollProvider } from './providers/SmoothScrollProvider'
import { ThemeProvider } from './providers/ThemeProvider'
import { ToastProvider } from './providers/ToastProvider'
import { AuthProvider } from './providers/AuthProvider'
import './lib/supabase'

const sentryDsn = import.meta.env.VITE_SENTRY_DSN
if (sentryDsn) {
  Sentry.init({
    dsn: sentryDsn,
    beforeSend(event) {
      if (event.request) {
        delete event.request.data
        delete event.request.headers
        delete event.request.cookies
        if (event.request.url) {
          event.request.url = event.request.url.split('?')[0]
        }
      }
      delete event.user
      return event
    },
  })
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ToastProvider>
          <AuthProvider>
            <SmoothScrollProvider>
              <BrowserRouter>
                <App />
              </BrowserRouter>
            </SmoothScrollProvider>
          </AuthProvider>
        </ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
)
