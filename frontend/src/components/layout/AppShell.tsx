import { useState, type ReactNode } from 'react'
import { ArrowUpRight, Menu, X } from 'lucide-react'
import { Link, NavLink } from 'react-router-dom'
import { ScrollProgress } from '../motion/ScrollProgress'
import { ThemeToggle } from './ThemeToggle'
import { useAuth } from '../../providers/useAuth'
import { useToast } from '../../providers/useToast'

const navigation = [
  { to: '/#how-it-works', label: 'How it works', end: false },
  { to: '/#features', label: 'Features', end: false },
  { to: '/#trust', label: 'Our approach', end: false },
]

export function AppShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const { user, signOut } = useAuth()
  const toast = useToast()

  async function handleSignOut() {
    try {
      await signOut()
      setMenuOpen(false)
    } catch {
      toast('Unable to sign out. Please try again.', 'error')
    }
  }

  return (
    <div className="app-shell">
      <ScrollProgress />
      <header className="site-header">
        <div className="site-header__inner">
          <Link aria-label="FinTax AI home" className="brand" to="/">
            <span className="brand__mark" aria-hidden="true">
              f<span>.</span>
            </span>
            <span className="brand__name">fintax<span>ai</span></span>
          </Link>

          <nav aria-label="Main navigation" className="desktop-nav">
            {navigation.map((item) => (
              <a className="nav-link" href={item.to} key={item.label}>
                {item.label}
              </a>
            ))}
          </nav>

          <div className="site-header__actions">
            <ThemeToggle />
            {user ? (
              <>
                <Link className="button button--small button--nav" to="/dashboard">
                  Dashboard <ArrowUpRight aria-hidden="true" size={15} />
                </Link>
                <button className="nav-link nav-signout" onClick={() => void handleSignOut()} type="button">
                  Sign out
                </button>
              </>
            ) : (
              <>
                <Link className="nav-link nav-signin" to="/login">Sign in</Link>
                <Link className="button button--small button--nav" to="/signup">
                  Get started <ArrowUpRight aria-hidden="true" size={15} />
                </Link>
              </>
            )}
            <button
              aria-expanded={menuOpen}
              aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              className="icon-button menu-toggle"
              onClick={() => setMenuOpen((open) => !open)}
              type="button"
            >
              {menuOpen ? <X aria-hidden="true" size={20} /> : <Menu aria-hidden="true" size={20} />}
            </button>
          </div>
        </div>
        {menuOpen && (
          <nav aria-label="Mobile navigation" className="mobile-nav">
            {navigation.map((item) => (
              <a
                className="nav-link"
                href={item.to}
                key={item.label}
                onClick={() => setMenuOpen(false)}
              >
                {item.label}
              </a>
            ))}
            {user ? (
              <button className="nav-link nav-signout" onClick={() => void handleSignOut()} type="button">
                Sign out
              </button>
            ) : (
              <Link className="nav-link" onClick={() => setMenuOpen(false)} to="/login">Sign in</Link>
            )}
            <Link
              className="button button--small"
              onClick={() => setMenuOpen(false)}
              to={user ? '/dashboard' : '/signup'}
            >
              {user ? 'Open dashboard' : 'Start your journey'} <ArrowUpRight aria-hidden="true" size={15} />
            </Link>
          </nav>
        )}
      </header>

      <main id="main-content">{children}</main>

      <footer className="site-footer">
        <div className="site-footer__inner">
          <div>
            <Link aria-label="FinTax AI home" className="brand" to="/">
              <span className="brand__mark" aria-hidden="true">
                f<span>.</span>
              </span>
              <span className="brand__name">fintax<span>ai</span></span>
            </Link>
            <p className="site-footer__note">
              Tax decisions, made clearer.<br />
              Built for India, grounded in trust.
            </p>
          </div>
          <div className="site-footer__links">
            <a href="/#how-it-works">How it works</a>
            <a href="/#features">Features</a>
            <NavLink to="/chat">Ask FinTax</NavLink>
          </div>
          <p className="site-footer__copyright">
            © 2026 FinTax AI <span>·</span> Designed with financial privacy in mind.
          </p>
        </div>
      </footer>
    </div>
  )
}
