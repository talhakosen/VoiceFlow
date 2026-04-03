import { Container } from '@/components/ui/Container'
import { FadeUp, StaggerContainer, StaggerItem } from '@/components/ui/FadeUp'
import { HOW_IT_WORKS } from '@/lib/constants'

const iconPaths: Record<string, React.ReactNode> = {
  Download: (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth="1.5" stroke="currentColor" className="w-5 h-5">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  Mic: (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth="1.5" stroke="currentColor" className="w-5 h-5">
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3M8 22h8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  TrendingUp: (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth="1.5" stroke="currentColor" className="w-5 h-5">
      <path d="m22 7-8.5 8.5-5-5L2 17M22 7h-7M22 7v7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
}

export function HowItWorksSection() {
  return (
    <section id="nasil-calisir" className="section-padding bg-ink-2">
      <Container>
        <div className="text-center mb-16">
          <FadeUp>
            <span className="section-label text-brand-blue">Nasıl Çalışır</span>
          </FadeUp>
          <FadeUp delay={0.1}>
            <h2 className="text-4xl lg:text-5xl font-bold text-white tracking-tight mb-4">
              3 adımda başlayın.
            </h2>
          </FadeUp>
          <FadeUp delay={0.2}>
            <p className="text-lg text-white/45 max-w-2xl mx-auto">
              15 dakika içinde kurulum tamamlanır, aynı gün üretken olursunuz.
            </p>
          </FadeUp>
        </div>

        <StaggerContainer className="relative">
          {/* Connector line */}
          <div className="hidden lg:block absolute top-[30px] left-[calc(16.67%+3rem)] right-[calc(16.67%+3rem)] h-px bg-gradient-to-r from-transparent via-brand-blue/30 to-transparent" />

          <div className="grid lg:grid-cols-3 gap-8 lg:gap-12">
            {HOW_IT_WORKS.map((step, index) => (
              <StaggerItem key={step.step}>
                <div className="relative flex flex-col items-center text-center lg:items-start lg:text-left">
                  {/* Step icon + number */}
                  <div className="relative mb-7">
                    <div className="w-14 h-14 rounded-2xl bg-ink-3 border border-white/[0.09] flex items-center justify-center text-brand-blue-light">
                      {iconPaths[step.icon]}
                    </div>
                    <span className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-brand-blue text-white text-[10px] font-bold flex items-center justify-center font-mono">
                      {index + 1}
                    </span>
                  </div>

                  <h3 className="text-xl font-bold text-white mb-3">{step.title}</h3>
                  <p className="text-white/45 leading-relaxed text-sm">{step.description}</p>
                </div>
              </StaggerItem>
            ))}
          </div>
        </StaggerContainer>
      </Container>
    </section>
  )
}
