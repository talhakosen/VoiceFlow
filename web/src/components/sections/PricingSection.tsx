'use client'

import { motion } from 'framer-motion'
import { Container } from '@/components/ui/Container'
import { Button } from '@/components/ui/Button'
import { FadeUp } from '@/components/ui/FadeUp'

const SAVINGS_ROWS = [
  {
    label: 'Prompt başına token',
    before: '~800 token',
    after: '~200 token',
    saving: '75% azalma',
  },
  {
    label: 'Görev başına iterasyon',
    before: '4–6 tur',
    after: '1–2 tur',
    saving: '3x daha az',
  },
  {
    label: 'Aylık agent maliyeti',
    before: '$2.400',
    after: '$600',
    saving: '$1.800 tasarruf',
  },
]

export function PricingSection() {
  return (
    <section
      id="fiyatlandirma"
      className="section-padding bg-brand-navy relative overflow-hidden"
    >
      <div className="absolute inset-0 bg-hero-gradient opacity-60" />
      <div className="glow-orb w-[600px] h-[600px] bg-brand-blue/8 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
      <div className="absolute inset-0 dot-grid opacity-10" />

      <Container size="lg" className="relative z-10">
        {/* Header */}
        <div className="text-center mb-16">
          <FadeUp>
            <span className="section-label text-brand-blue">
              Fiyatlandırma
            </span>
          </FadeUp>
          <FadeUp delay={0.1}>
            <h2 className="text-4xl lg:text-5xl font-bold text-white tracking-tight leading-tight mb-5">
              Siz kazanıyorsunuz,
              <br />
              <span className="text-brand-blue-light">biz kazanıyoruz.</span>
            </h2>
          </FadeUp>
          <FadeUp delay={0.2}>
            <p className="text-lg text-text-muted max-w-2xl mx-auto">
              VoiceFlow&apos;u sizden para kazanmak için değil, size kazandırmak için yaptık.
              Agent ve token maliyetlerinizi düşürüyoruz — gelirini bu tasarruftan alıyoruz.
            </p>
          </FadeUp>
        </div>

        <div className="grid lg:grid-cols-2 gap-12 items-start">
          {/* Left: the model explained */}
          <FadeUp delay={0.1}>
            <div className="space-y-4">
              {[
                {
                  step: '01',
                  title: 'Ücretsiz kullanın',
                  desc: 'VoiceFlow\'u temel olarak ücretsiz kullanırsınız. Kurulum maliyeti yok, aylık abonelik yok.',
                },
                {
                  step: '02',
                  title: 'Token maliyetiniz düşer',
                  desc: 'Sesle yazdığınız promptlar daha net, daha kısa, daha az iterasyon gerektirir. AI harcamanız ciddi oranda azalır.',
                },
                {
                  step: '03',
                  title: 'Tasarrufunuzdan pay alıyoruz',
                  desc: 'Sizin için yarattığımız değerin bir bölümünü paylaşıyoruz. Sizi kazanmazsak, biz de kazanmıyoruz.',
                },
              ].map((item) => (
                <div
                  key={item.step}
                  className="flex gap-5 p-6 rounded-2xl bg-white/[0.04] border border-white/[0.08] hover:border-brand-blue/30 transition-colors"
                >
                  <span className="text-xs font-bold text-brand-blue/50 font-mono mt-0.5 shrink-0 w-6">
                    {item.step}
                  </span>
                  <div>
                    <h3 className="font-semibold text-white mb-1">{item.title}</h3>
                    <p className="text-sm text-text-muted leading-relaxed">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </FadeUp>

          {/* Right: savings table */}
          <FadeUp delay={0.25}>
            <div className="rounded-2xl bg-white/[0.05] border border-white/[0.10] overflow-hidden">
              <div className="px-6 py-5 border-b border-white/[0.08]">
                <p className="text-sm font-semibold text-white">
                  Ortalama Maliyet Karşılaştırması
                </p>
                <p className="text-xs text-text-muted mt-1">10 kişilik geliştirici ekibi — aylık</p>
              </div>

              {/* Table header */}
              <div className="grid grid-cols-4 px-6 py-3 text-xs font-semibold text-text-muted uppercase tracking-wide border-b border-white/[0.06]">
                <span className="col-span-1">Kalem</span>
                <span className="text-center">Öncesi</span>
                <span className="text-center text-brand-blue-light">VoiceFlow ile</span>
                <span className="text-right text-accent-green">Tasarruf</span>
              </div>

              {SAVINGS_ROWS.map((row, i) => (
                <div
                  key={row.label}
                  className={`grid grid-cols-4 px-6 py-4 text-sm items-center ${
                    i !== SAVINGS_ROWS.length - 1 ? 'border-b border-white/[0.05]' : ''
                  }`}
                >
                  <span className="text-text-secondary col-span-1 text-xs">{row.label}</span>
                  <span className="text-center text-text-muted line-through decoration-red-400/50 text-xs">
                    {row.before}
                  </span>
                  <span className="text-center text-brand-blue-light font-medium text-xs">
                    {row.after}
                  </span>
                  <span className="text-right text-accent-green font-semibold text-xs">
                    {row.saving}
                  </span>
                </div>
              ))}

              <div className="px-6 py-5 bg-accent-green/5 border-t border-accent-green/15">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-bold text-white">Yıllık tasarruf</p>
                    <p className="text-xs text-text-muted mt-0.5">Bu tasarruftan pay alıyoruz</p>
                  </div>
                  <div className="text-right">
                    <motion.p
                      className="text-2xl font-bold text-accent-green"
                      initial={{ opacity: 0, scale: 0.8 }}
                      whileInView={{ opacity: 1, scale: 1 }}
                      viewport={{ once: true }}
                      transition={{ delay: 0.5, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                    >
                      $21.600
                    </motion.p>
                    <p className="text-xs text-text-muted">ekip başına</p>
                  </div>
                </div>
              </div>
            </div>

            <p className="text-xs text-text-muted/50 text-center mt-4">
              * Gerçek tasarruf kullanım profiline göre değişir. Pilot programda ölçüyoruz.
            </p>
          </FadeUp>
        </div>

        {/* CTA */}
        <FadeUp delay={0.3}>
          <div className="text-center mt-16">
            <Button variant="primary" size="lg" className="text-base px-10">
              Ücretsiz Pilot Başlatın
            </Button>
            <p className="text-sm text-text-muted mt-4">
              Kredi kartı gerekmez · 14 gün ücretsiz · Verileriniz sizde kalır
            </p>
          </div>
        </FadeUp>
      </Container>
    </section>
  )
}
