export interface NavLink {
  label: string
  href: string
}

export interface Feature {
  icon: string
  title: string
  description: string
  highlight?: boolean
}

export interface Stat {
  value: string
  suffix: string
  label: string
  description: string
}

export interface TrustBadge {
  label: string
  icon: string
  description: string
}

export interface Step {
  step: string
  title: string
  description: string
  icon: string
}

export interface Testimonial {
  quote: string
  author: string
  title: string
  company: string
  avatar: string
}

export interface PricingTier {
  name: string
  price: string
  period: string
  description: string
  features: string[]
  cta: string
  highlighted: boolean
}

export interface ComparisonRow {
  feature: string
  keyboard: string
  voice: string
}

export interface FooterColumn {
  title: string
  links: Array<{ label: string; href: string }>
}

export interface SocialLink {
  label: string
  href: string
  icon: string
}

export interface AgenticUseCase {
  icon: string
  title: string
  description: string
  example: {
    raw: string
    label: string
  }
  highlight?: boolean
}
