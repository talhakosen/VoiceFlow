import { cn } from '@/lib/utils'

export type BadgeVariant = 'default' | 'blue' | 'green' | 'purple' | 'outline'

export interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant
  dot?: boolean
  className?: string
}

const variantClasses: Record<BadgeVariant, string> = {
  default: 'bg-surface-muted text-text-secondary',
  blue: 'bg-brand-blue/10 text-brand-blue border border-brand-blue/20',
  green: 'bg-accent-green/10 text-accent-green border border-accent-green/20',
  purple: 'bg-brand-blue-purple/10 text-brand-blue-purple border border-brand-blue-purple/20',
  outline: 'bg-transparent border border-text-muted/30 text-text-secondary',
}

const dotVariantClasses: Record<BadgeVariant, string> = {
  default: 'bg-text-muted',
  blue: 'bg-brand-blue',
  green: 'bg-accent-green',
  purple: 'bg-brand-blue-purple',
  outline: 'bg-text-muted',
}

export function Badge({
  children,
  variant = 'default',
  dot = false,
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-medium',
        variantClasses[variant],
        className
      )}
    >
      {dot && (
        <span
          className={cn(
            'w-1.5 h-1.5 rounded-full shrink-0',
            dotVariantClasses[variant]
          )}
        />
      )}
      {children}
    </span>
  )
}
