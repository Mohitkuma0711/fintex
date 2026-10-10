import { useState, type FormEvent } from 'react'
import { ArrowLeft, Mail, ShieldCheck } from 'lucide-react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../providers/AuthProvider'

type AuthMode = 'sign-in' | 'sign-up'

export function AuthPage() {
  const location = useLocation()
  const { signInWithEmail, signInWithGoogle, signUpWithEmail, user } = useAuth()
  const [mode, setMode] = useState<AuthMode>('sign-in')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? '/upload'

  if (user) {
    return <Navigate replace to={from} />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      if (mode === 'sign-in') {
        await signInWithEmail(email, password)
      } else {
        await signUpWithEmail(email, password)
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Authentication failed.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleGoogle() {
    setError(null)
    setSubmitting(true)
    try {
      await signInWithGoogle()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Google sign-in failed.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="auth-page">
      <Link className="auth-page__back" to="/">
        <span>
          <ArrowLeft aria-hidden="true" size={18} />
          Home
        </span>
      </Link>

      <div className="auth-card">
        <div className="auth-card__mark" aria-hidden="true">
          <ShieldCheck size={28} />
          <span>Supabase secured</span>
        </div>
        <p className="eyebrow">Private tax workspace</p>
        <h1>{mode === 'sign-in' ? 'Sign in to FinTax AI' : 'Create your FinTax AI account'}</h1>
        <p className="auth-card__intro">
          Your account is secured by Supabase. Your tax documents stay private and encrypted.
        </p>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Email
            <input
              autoComplete="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>
          <label>
            Password
            <input
              autoComplete={mode === 'sign-in' ? 'current-password' : 'new-password'}
              minLength={6}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>
          {error && <p className="auth-form__error">{error}</p>}
          <button className="auth-form__submit" disabled={submitting} type="submit">
            <Mail aria-hidden="true" size={17} />
            {mode === 'sign-in' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        <button className="auth-form__submit" disabled={submitting} onClick={handleGoogle} type="button">
          Continue with Google
        </button>

        <p className="auth-card__switch">
          {mode === 'sign-in' ? 'New here?' : 'Already have an account?'}{' '}
          <button
            onClick={() => setMode(mode === 'sign-in' ? 'sign-up' : 'sign-in')}
            type="button"
          >
            {mode === 'sign-in' ? 'Create an account' : 'Sign in'}
          </button>
        </p>
      </div>
    </section>
  )
}
