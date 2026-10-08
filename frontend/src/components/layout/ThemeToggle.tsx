import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../../providers/useTheme'

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  const nextTheme = theme === 'light' ? 'dark' : 'light'
  const Icon = theme === 'light' ? Moon : Sun

  return (
    <button
      aria-label={`Switch to ${nextTheme} theme`}
      className="icon-button"
      onClick={toggleTheme}
      type="button"
    >
      <Icon aria-hidden="true" size={18} />
    </button>
  )
}
