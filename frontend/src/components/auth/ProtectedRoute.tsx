import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../../providers/useAuth'
import { Skeleton } from '../ui/Skeleton'

export function ProtectedRoute() {
  const { user, loading, authError } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <section aria-label="Loading account" className="auth-page container">
        <Skeleton className="auth-card__skeleton" />
      </section>
    )
  }

  if (!user) {
    const next = `${location.pathname}${location.search}`
    return <Navigate replace state={{ next }} to="/login" />
  }

  return authError ? (
    <section className="auth-page container">
      <p className="auth-form__error" role="alert">{authError}</p>
    </section>
  ) : <Outlet />
}
