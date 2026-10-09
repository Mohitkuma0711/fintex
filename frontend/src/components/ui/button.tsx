import type { ButtonHTMLAttributes } from 'react'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'light' | 'nav' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
}

export function Button({
  className = '',
  variant = 'primary',
  size = 'md',
  type = 'button',
  ...props
}: ButtonProps) {
  const variantClass =
    variant === 'primary'
      ? 'button--primary'
      : variant === 'light'
        ? 'button--light'
        : variant === 'nav'
          ? 'button--nav'
          : ''

  const sizeClass = size === 'sm' ? 'button--small' : ''

  return (
    <button
      className={`button ${variantClass} ${sizeClass} ${className}`.trim()}
      type={type}
      {...props}
    />
  )
}
