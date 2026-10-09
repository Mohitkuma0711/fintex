import { AnimatePresence } from 'framer-motion'
import { Route, Routes, useLocation } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { LandingPage } from '../pages/LandingPage'
import { AuthPage } from '../pages/AuthPage'
import { UploadPage } from '../pages/UploadPage'
import { ReportPage } from '../pages/ReportPage'
import { FilingGuidancePage } from '../pages/FilingGuidancePage'
import { DashboardPage } from '../pages/DashboardPage'
import { SimulatorPage } from '../pages/SimulatorPage'
import { ChatPage } from '../pages/ChatPage'
import { PlaceholderPage } from '../pages/PlaceholderPage'
import { PageTransition } from '../components/motion/PageTransition'
import { ProtectedRoute } from '../components/auth/ProtectedRoute'

export function App() {
  const location = useLocation()

  return (
    <AppShell>
      <AnimatePresence mode="wait">
        <PageTransition key={location.pathname}>
          <Routes location={location}>
            <Route path="/" element={<LandingPage />} />
            <Route path="/auth" element={<AuthPage />} />
            <Route path="/upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
            <Route path="/report" element={<ProtectedRoute><ReportPage /></ProtectedRoute>} />
            <Route path="/filing-guidance" element={<ProtectedRoute><FilingGuidancePage /></ProtectedRoute>} />
            <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
            <Route path="/simulator" element={<ProtectedRoute><SimulatorPage /></ProtectedRoute>} />
            <Route path="/chat" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
            <Route path="*" element={<PlaceholderPage page="not-found" />} />
          </Routes>
        </PageTransition>
      </AnimatePresence>
    </AppShell>
  )
}
