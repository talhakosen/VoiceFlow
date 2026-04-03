import { cn } from '@/lib/utils'

export interface GradientTextProps {
  children: React.ReactNode
  className?: string
  as?: 'span' | 'h1' | 'h2' | 'h3' | 'h4' | 'p' | 'div'
  animated?: boolean
}

export function GradientText({
  children,
  className,
  as: Tag = 'span',
  animated = true,
}: GradientTextProps) {
  return (
    <Tag
      className={cn(
        'bg-gradient-to-r from-brand-blue-light via-brand-blue-purple to-brand-blue-light bg-clip-text text-transparent',
        animated && 'animate-gradient-shift bg-[length:200%_auto]',
        className
      )}
    >
      {children}
    </Tag>
  )
}
