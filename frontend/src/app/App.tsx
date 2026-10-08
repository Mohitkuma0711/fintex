import { lazy, Suspense } from 'react'
import { AnimatePresence } from 'framer-motion'
import { Route, Routes, useLocation } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { PageTransition } from '../components/motion/PageTransition'
import { ProtectedRoute } from '../components/auth/ProtectedRoute'
import { AuthPage } from '../pages/AuthPage'
import { LandingPage } from '../pages/LandingPage'
import { PlaceholderPage } from '../pages/PlaceholderPage'
import { ReviewPage } from '../pages/ReviewPage'
import { UploadPage } from '../pages/UploadPage'

const DashboardPage = lazy(async () => {
  const module = await import('../pages/DashboardPage')
  return { default: module.DashboardPage }
})
const SimulatorPage = lazy(async () => {
  const module = await import('../pages/SimulatorPage')
  return { default: module.SimulatorPage }
})

export function App() {
  const location = useLocation()

  return (
    <AppShell>
      <AnimatePresence mode="wait">
        <PageTransition key={location.pathname}>
          <Routes location={location}>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<AuthPage mode="login" />} />
            <Route path="/signup" element={<AuthPage mode="signup" />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/onboarding" element={<PlaceholderPage page="onboarding" />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/review" element={<ReviewPage />} />
              <Route path="/dashboard" element={<Suspense fallback={<main className="container"><p role="status">Loading your tax workspace…</p></main>}><DashboardPage /></Suspense>} />
              <Route path="/simulator" element={<Suspense fallback={<main className="container"><p role="status">Loading the scenario simulator…</p></main>}><SimulatorPage /></Suspense>} />
              <Route path="/chat" element={<PlaceholderPage page="chat" />} />
              <Route path="/report" element={<PlaceholderPage page="report" />} />
            </Route>
            <Route path="*" element={<PlaceholderPage page="not-found" />} />
          </Routes>
        </PageTransition>
      </AnimatePresence>
    </AppShell>
  )
}
