import { cn } from '@/lib/utils'

export type CardVariant = 'default' | 'glass' | 'dark' | 'bordered'

export interface CardProps {
  children: React.ReactNode
  variant?: CardVariant
  className?: string
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

const variantClasses: Record<CardVariant, string> = {
  default: 'bg-white shadow-card',
  glass:
    'bg-white/[0.06] backdrop-blur-xl border border-white/[0.1] shadow-card',
  dark: 'bg-brand-navy-light border border-white/[0.08]',
  bordered: 'bg-white border border-surface-muted shadow-card',
}

const paddingClasses = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
}

export function Card({
  children,
  variant = 'default',
  padding = 'md',
  className,
}: CardProps) {
  return (
    <div
      className={cn(
        'rounded-card overflow-hidden',
        variantClasses[variant],
        paddingClasses[padding],
        className
      )}
    >
      {children}
    </div>
  )
}
