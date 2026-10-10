import { useState, type ReactNode } from 'react'
import { ArrowUpRight, Menu, X } from 'lucide-react'
import { Link, NavLink } from 'react-router-dom'
import { ScrollProgress } from '../motion/ScrollProgress'
import { ThemeToggle } from './ThemeToggle'
import { useAuth } from '../../providers/AuthProvider'

const navLinks = [
  { to: '/upload', label: 'Upload' },
  { to: '/simulator', label: 'Simulator' },
  { to: '/filing-guidance', label: 'Filing Guide' },
  { to: '/rules', label: 'Tax Rules' },
  { to: '/advisor', label: 'Tax Advisor' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/chat', label: 'Ask FinTax' },
]

export function AppShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const { signOutUser, user } = useAuth()

  return (
    <div className="app-shell">
      <ScrollProgress />
      <header className="site-header">
        <div className="site-header__inner">
          <Link aria-label="FinTax AI home" className="brand" to="/">
            <span className="brand__mark" aria-hidden="true">
              f<span>.</span>
            </span>
            <span className="brand__name">
              fintax<span>ai</span>
            </span>
            <span
              style={{
                marginLeft: '0.5rem',
                fontSize: '0.68rem',
                fontWeight: 600,
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
                padding: '2px 8px',
                borderRadius: '999px',
                background: 'var(--brand-soft)',
                color: 'var(--brand)',
                border: '1px solid var(--line)',
                display: 'none',
              }}
              className="hidden sm:inline-block"
            >
              India AI Tax Platform
            </span>
          </Link>

          <nav aria-label="Main navigation" className="desktop-nav">
            {navLinks.map((item) => (
              <NavLink
                className={({ isActive }) =>
                  `nav-link${isActive ? ' text-brand font-bold' : ''}`
                }
                key={item.label}
                to={item.to}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="site-header__actions">
            <ThemeToggle />
            {user ? (
              <button className="button button--small button--nav" onClick={signOutUser} type="button">
                Sign out
              </button>
            ) : (
              <Link className="button button--small button--nav" to="/auth">
                Sign in <ArrowUpRight aria-hidden="true" size={15} />
              </Link>
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
            {navLinks.map((item) => (
              <NavLink
                className="nav-link"
                key={item.label}
                onClick={() => setMenuOpen(false)}
                to={item.to}
              >
                {item.label}
              </NavLink>
            ))}
            {user ? (
              <button
                className="button button--small"
                onClick={() => {
                  setMenuOpen(false)
                  void signOutUser()
                }}
                type="button"
              >
                Sign out
              </button>
            ) : (
              <Link className="button button--small" onClick={() => setMenuOpen(false)} to="/auth">
                Sign in <ArrowUpRight aria-hidden="true" size={15} />
              </Link>
            )}
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
              <span className="brand__name">
                fintax<span>ai</span>
              </span>
            </Link>
            <p className="site-footer__note">
              Tax decisions, made clearer. Grounded in official IT Act rules.
              <br />
              <span style={{ fontSize: '0.72rem', opacity: 0.85 }}>
                Not a substitute for certified CA advice for complex corporate filings.
              </span>
            </p>
          </div>
          <div className="site-footer__links">
            <Link to="/upload">Upload</Link>
            <Link to="/simulator">Tax Simulator</Link>
            <Link to="/filing-guidance">Filing Guide</Link>
            <Link to="/dashboard">Dashboard</Link>
            <Link to="/chat">Ask FinTax</Link>
          </div>
          <p className="site-footer__copyright">
            © 2026 FinTax AI <span>·</span> Designed with financial privacy in mind.
          </p>
        </div>
      </footer>
    </div>
  )
}
