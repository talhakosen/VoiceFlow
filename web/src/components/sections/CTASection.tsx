import { Container } from '@/components/ui/Container'
import { Button } from '@/components/ui/Button'
import { CTA_SECTION } from '@/lib/constants'

export function CTASection() {
  return (
    <section className="section-padding bg-brand-navy relative overflow-hidden">
      <div className="absolute inset-0 bg-hero-gradient" />
      <div className="glow-orb w-[600px] h-[600px] bg-brand-blue/12 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
      <div className="glow-orb w-[300px] h-[300px] bg-brand-blue-purple/15 top-0 right-0" />
      <div className="glow-orb w-[300px] h-[300px] bg-brand-blue/10 bottom-0 left-0" />
      <div className="absolute inset-0 dot-grid opacity-15" />

      <Container size="md" className="relative z-10 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-pill bg-white/[0.06] border border-white/[0.12] text-brand-blue-light text-sm font-medium mb-8">
          <span className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
          14 gün ücretsiz pilot
        </div>

        <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white leading-tight tracking-tight mb-6">
          {CTA_SECTION.title}
        </h2>

        <p className="text-xl text-text-muted leading-relaxed mb-10 max-w-2xl mx-auto">
          {CTA_SECTION.subtitle}
        </p>

        <div className="flex flex-wrap gap-4 justify-center mb-6">
          <Button size="lg" variant="primary" className="text-base px-10">
            {CTA_SECTION.ctaPrimary}
          </Button>
          <Button
            size="lg"
            variant="ghost"
            className="text-white hover:bg-white/10 hover:text-white text-base"
          >
            {CTA_SECTION.ctaSecondary}
          </Button>
        </div>
        <p className="text-sm text-text-muted">{CTA_SECTION.disclaimer}</p>

        <div className="flex flex-wrap justify-center gap-6 mt-12 pt-12 border-t border-white/[0.08]">
          {[
            {
              icon: (
                <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" stroke="currentColor" className="w-4 h-4">
                  <rect x="3" y="11" width="18" height="11" rx="2" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ),
              text: 'On-Premise Kurulum',
            },
            {
              icon: (
                <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" stroke="currentColor" className="w-4 h-4">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ),
              text: 'KVKK Uyumlu',
            },
            {
              icon: (
                <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" stroke="currentColor" className="w-4 h-4">
                  <circle cx="12" cy="12" r="10" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10zM2 12h20" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ),
              text: 'Türkçe Destek',
            },
            {
              icon: (
                <svg viewBox="0 0 24 24" fill="none" strokeWidth="2" stroke="currentColor" className="w-4 h-4">
                  <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ),
              text: 'SLA Garantisi',
            },
          ].map((item) => (
            <div key={item.text} className="flex items-center gap-2 text-sm text-text-muted">
              <span className="text-brand-blue-light">{item.icon}</span>
              <span>{item.text}</span>
            </div>
          ))}
        </div>
      </Container>
    </section>
  )
}
