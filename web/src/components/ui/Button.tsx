'use client'

import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

export type ButtonVariant = 'primary' | 'ghost' | 'outline'
export type ButtonSize = 'sm' | 'md' | 'lg'

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  icon?: React.ReactNode
  iconPosition?: 'left' | 'right'
  loading?: boolean
  href?: string
}

// Birincil buton signal kullanır ve ekrandaki tek amber nesnedir.
// Görünür alanda iki birincil buton varsa biri ghost/outline olmalı.
const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-signal text-text-on-signal hover:brightness-95 active:brightness-90',
  ghost:
    'bg-transparent text-text-muted hover:text-text hover:bg-control active:bg-control-hover',
  outline:
    'bg-transparent border border-line-strong text-text hover:bg-control active:bg-control-hover',
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'px-s-4 py-s-2 text-web-small gap-s-2 rounded-md min-h-[36px]',
  md: 'px-s-5 py-s-3 text-web-small gap-s-2 rounded-md min-h-[44px]',
  lg: 'px-s-6 py-s-4 text-web-body gap-s-3 rounded-md min-h-[52px]',
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      icon,
      iconPosition = 'left',
      loading = false,
      className,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          'inline-flex items-center justify-center font-medium transition-colors duration-200 cursor-pointer select-none whitespace-nowrap',
          'focus-visible:outline-none focus-visible:shadow-focus',
          'disabled:text-text-faint disabled:cursor-not-allowed',
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
        {...props}
      >
        {loading && (
          <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        )}
        {!loading && icon && iconPosition === 'left' && (
          <span className="shrink-0">{icon}</span>
        )}
        {children}
        {!loading && icon && iconPosition === 'right' && (
          <span className="shrink-0">{icon}</span>
        )}
      </button>
    )
  }
)

Button.displayName = 'Button'

export { Button }
