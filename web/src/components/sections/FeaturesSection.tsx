import { Container } from '@/components/ui/Container'
import { FadeUp, StaggerContainer, StaggerItem } from '@/components/ui/FadeUp'
import { FEATURES } from '@/lib/constants'
import { cn } from '@/lib/utils'

const iconPaths: Record<string, React.ReactNode> = {
  Mic: (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" stroke="currentColor" className="w-6 h-6">
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3M8 22h8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  Brain: (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" stroke="currentColor" className="w-6 h-6">
      <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4M9 12a4.5 4.5 0 0 0 3 4 4.5 4.5 0 0 0 3-4M8 12h8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  Lock: (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" stroke="currentColor" className="w-6 h-6">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  Building2: (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" stroke="currentColor" className="w-6 h-6">
      <path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18ZM6 12H4a2 2 0 0 0-2 2v8h4M18 9h2a2 2 0 0 1 2 2v11h-4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M10 6h4M10 10h4M10 14h4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  Globe: (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" stroke="currentColor" className="w-6 h-6">
      <circle cx="12" cy="12" r="10" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10zM2 12h20" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  Zap: (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" stroke="currentColor" className="w-6 h-6">
      <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
}

export function FeaturesSection() {
  return (
    <section className="section-padding bg-brand-navy relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-hero-gradient opacity-60" />
      <div className="absolute inset-0 dot-grid opacity-20" />
      <div className="glow-orb w-[500px] h-[500px] bg-brand-blue-purple/8 top-[-200px] left-[-100px]" />
      <div className="glow-orb w-[400px] h-[400px] bg-brand-blue/8 bottom-[-100px] right-[-100px]" />

      <Container className="relative z-10">
        <div className="text-center mb-16">
          <FadeUp>
            <span className="section-label text-brand-blue">
              Yetenekler
            </span>
          </FadeUp>
          <FadeUp delay={0.1}>
            <h2 className="text-4xl lg:text-5xl font-bold text-white tracking-tight mb-4">
              Kurumsal standartlarda
              <br />
              <span className="text-brand-blue-light">tüm özellikler dahil.</span>
            </h2>
          </FadeUp>
          <FadeUp delay={0.2}>
            <p className="text-lg text-white/45 max-w-2xl mx-auto">
              Ses tanımadan yapay zeka düzeltmeye, güvenlikten entegrasyona —
              ihtiyacınız olan her şey tek platformda.
            </p>
          </FadeUp>
        </div>

        <StaggerContainer className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((feature) => (
            <StaggerItem key={feature.title}>
              <div
                className={cn(
                  'relative rounded-card p-6 h-full flex flex-col transition-all duration-300 group cursor-default',
                  'bg-white/[0.05] border backdrop-blur-sm',
                  feature.highlight
                    ? 'border-brand-blue/40 hover:border-brand-blue/60 hover:bg-white/[0.08]'
                    : 'border-white/[0.08] hover:border-white/[0.18] hover:bg-white/[0.07]'
                )}
              >
                {feature.highlight && (
                  <div className="absolute inset-0 rounded-card bg-gradient-to-br from-brand-blue/5 to-brand-blue-purple/5 pointer-events-none" />
                )}

                {/* Icon */}
                <div
                  className={cn(
                    'w-12 h-12 rounded-card-sm flex items-center justify-center mb-5 transition-colors',
                    feature.highlight
                      ? 'bg-brand-blue/10 text-brand-blue-light'
                      : 'bg-white/10 text-text-muted group-hover:text-white group-hover:bg-white/20'
                  )}
                >
                  {iconPaths[feature.icon]}
                </div>

                <h3 className="text-lg font-bold text-white mb-3">{feature.title}</h3>
                <p className="text-sm text-text-muted leading-relaxed flex-1">
                  {feature.description}
                </p>

                {feature.highlight && (
                  <div className="mt-4 pt-4 border-t border-brand-blue/15">
                    <span className="text-xs text-brand-blue-light font-medium">
                      Kurumsal Tercih
                    </span>
                  </div>
                )}
              </div>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </Container>
    </section>
  )
}
