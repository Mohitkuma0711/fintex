import { useState, type FormEvent } from 'react'
import { z } from 'zod'
import { ArrowLeft, ArrowRight, LockKeyhole } from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../providers/useAuth'

const credentialsSchema = z.object({
  email: z.email(),
  password: z.string().min(8, 'Use at least 8 characters for your password.'),
})

interface AuthPageProps {
  mode: 'login' | 'signup'
}

export function AuthPage({ mode }: AuthPageProps) {
  const { configured, authError, signIn, signUp } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const isSignup = mode === 'signup'

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setNotice('')
    const credentials = credentialsSchema.safeParse({ email: email.trim(), password })
    if (!credentials.success) {
      setError(credentials.error.issues[0]?.message ?? 'Enter valid sign-in details.')
      return
    }
    if (!configured) {
      setError('Authentication is not configured. Add the Supabase URL and public anon key.')
      return
    }

    setSubmitting(true)
    try {
      if (isSignup) {
        const hasSession = await signUp(credentials.data.email, credentials.data.password)
        if (!hasSession) {
          setNotice('Check your email for the Supabase confirmation link to finish creating your account.')
          return
        }
      } else {
        await signIn(credentials.data.email, credentials.data.password)
      }
      const state = location.state as { next?: unknown } | null
      const next = typeof state?.next === 'string' && state.next.startsWith('/') &&
        !state.next.startsWith('//')
        ? state.next
        : '/dashboard'
      navigate(next, { replace: true })
    } catch (authError) {
      setError(authError instanceof Error ? authError.message : 'Unable to complete authentication.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="auth-page container">
      <div className="auth-page__back">
        <Link className="text-link" to="/">
          <ArrowLeft aria-hidden="true" size={15} /> FinTax AI home
        </Link>
        <span><LockKeyhole aria-hidden="true" size={14} /> Secure Supabase sign-in</span>
      </div>
      <div className="auth-card">
        <div aria-hidden="true" className="auth-card__mark">f<span>.</span></div>
        <p className="eyebrow">{isSignup ? 'YOUR PRIVATE TAX WORKSPACE' : 'WELCOME BACK'}</p>
        <h1>{isSignup ? 'Create your account.' : 'Sign in to FinTax AI.'}</h1>
        <p className="auth-card__intro">
          {isSignup
            ? 'Your account is secured by Supabase. Your tax documents stay private.'
            : 'Continue to your private, personalized tax workspace.'}
        </p>
        {!configured && (
          <div className="auth-notice" role="status">
            Supabase is not configured in this environment. Add the values from
            <code>frontend/.env.example</code> to <code>frontend/.env.local</code> and restart Vite.
          </div>
        )}
        {authError && <p className="auth-form__error" role="alert">{authError}</p>}
        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="auth-email">Email address</label>
          <input
            autoComplete="email"
            id="auth-email"
            name="email"
            onChange={(event) => setEmail(event.target.value)}
            required
            type="email"
            value={email}
          />
          <label htmlFor="auth-password">Password</label>
          <input
            autoComplete={isSignup ? 'new-password' : 'current-password'}
            id="auth-password"
            minLength={8}
            name="password"
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
          {error && <p className="auth-form__error" role="alert">{error}</p>}
          {notice && <p className="auth-form__notice" role="status">{notice}</p>}
          <button className="button button--primary auth-form__submit" disabled={submitting} type="submit">
            {submitting ? 'Please wait…' : isSignup ? 'Create account' : 'Sign in'}
            <ArrowRight aria-hidden="true" size={16} />
          </button>
        </form>
        <p className="auth-card__switch">
          {isSignup ? 'Already have an account?' : 'New to FinTax AI?'}{' '}
          <Link to={isSignup ? '/login' : '/signup'}>{isSignup ? 'Sign in' : 'Create an account'}</Link>
        </p>
      </div>
    </section>
  )
}
