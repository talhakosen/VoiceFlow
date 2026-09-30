import { cn } from '@/lib/utils'

export type BadgeVariant =
  | 'default'
  | 'signal'
  | 'positive'
  | 'caution'
  | 'critical'
  | 'general'
  | 'engineering'
  | 'office'
  | 'outline'

export interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant
  dot?: boolean
  className?: string
}

// Dolgu rengin %20 saydamı, yazı rengin kendisi. Dolu renk kullanılmaz:
// rozet bir uyarı değil, bir etikettir.
const variantClasses: Record<BadgeVariant, string> = {
  default: 'bg-control text-text-muted',
  signal: 'bg-signal/20 text-signal-text',
  positive: 'bg-positive/20 text-positive',
  caution: 'bg-caution/20 text-caution',
  critical: 'bg-critical/20 text-critical',
  general: 'bg-mode-general/20 text-mode-general',
  engineering: 'bg-mode-engineering/20 text-mode-engineering',
  office: 'bg-mode-office/20 text-mode-office',
  outline: 'bg-transparent border border-line-strong text-text-muted',
}

const dotVariantClasses: Record<BadgeVariant, string> = {
  default: 'bg-text-faint',
  signal: 'bg-signal',
  positive: 'bg-positive',
  caution: 'bg-caution',
  critical: 'bg-critical',
  general: 'bg-mode-general',
  engineering: 'bg-mode-engineering',
  office: 'bg-mode-office',
  outline: 'bg-text-faint',
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
        'inline-flex items-center gap-s-2 px-s-2 py-s-1 rounded-sm font-mono text-data-s uppercase tracking-wide',
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
