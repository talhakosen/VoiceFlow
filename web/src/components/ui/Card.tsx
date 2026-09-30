import { cn } from '@/lib/utils'

export type CardVariant = 'default' | 'sunken' | 'signal' | 'bordered'

export interface CardProps {
  children: React.ReactNode
  variant?: CardVariant
  className?: string
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

// Kartlar gölgeyle değil çizgiyle ayrılır. Cam efekti yok:
// saydamlık arkasında ne olduğunu gizler, bu sistem gizlemez.
const variantClasses: Record<CardVariant, string> = {
  default: 'bg-surface-raised border border-line',
  sunken: 'bg-surface-sunken border border-line',
  // Dikkat isteyen tek grup için — sayfada en fazla bir tane.
  signal: 'bg-surface-raised border border-signal',
  bordered: 'bg-transparent border border-line',
}

const paddingClasses = {
  none: '',
  sm: 'p-s-4',
  md: 'p-s-6',
  lg: 'p-s-8',
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
        'rounded-lg overflow-hidden',
        variantClasses[variant],
        paddingClasses[padding],
        className
      )}
    >
      {children}
    </div>
  )
}
