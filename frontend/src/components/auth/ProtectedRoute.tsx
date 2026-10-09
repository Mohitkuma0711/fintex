import { Navigate, useLocation } from 'react-router-dom'
import type { ReactElement } from 'react'
import { useAuth } from '../../providers/AuthProvider'

export function ProtectedRoute({ children }: { children: ReactElement }) {
  const location = useLocation()
  const { loading, user } = useAuth()

  if (loading) {
    return <div className="page-loader">Loading secure workspace...</div>
  }

  if (!user) {
    return <Navigate replace state={{ from: location }} to="/auth" />
  }

  return children
}
