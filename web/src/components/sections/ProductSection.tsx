'use client'

import { motion } from 'framer-motion'
import { Container } from '@/components/ui/Container'
import { FadeUp } from '@/components/ui/FadeUp'

const USE_CASES = [
  {
    label: 'Ofis',
    tagline: 'E-posta, rapor, toplantı notu',
    description: 'Konuşarak dikte edin, kusursuz Türkçe çıksın. Şablonlarla tek komutla hazır metin oluşturun.',
    examples: [
      {
        title: 'Sesli dikte',
        said: 'bugun toplantida konustugumuz butce planlamasi konusunu tekrar gozmden gecirelim',
        got: 'Bugün toplantıda konuştuğumuz bütçe planlaması konusunu tekrar gözden geçirelim.',
      },
      {
        title: 'Şablon kullanımı',
        said: 'kurumsal e-posta',
        got: 'Sayın [İsim],\n\n[Konu] hakkındaki talebiniz değerlendirilmiştir.\n\nDetaylar için ekte sunulan raporu incelemenizi rica ederiz.\n\nSaygılarımızla,\n[İmza]',
      },
    ],
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-5 h-5">
        <path d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
  },
  {
    label: 'Yazılım Geliştirme',
    tagline: 'Prompt, commit mesajı, kod yorumu',
    description: 'Teknik terimler korunur, dosya referansları otomatik enjekte edilir. Daha iyi prompt, daha iyi çıktı.',
    examples: [
      {
        title: 'Dosya referansı enjeksiyonu',
        said: 'auth servis tıken rıfres metodunu düzelt retry mekanizması ekle',
        got: 'AuthService @src/services/auth.ts:47 token refresh metodunu düzelt, retry mekanizması ekle.',
      },
      {
        title: 'Teknik terim düzeltme',
        said: 'apvyumodel state yönetimini rıdüser paternine geçir',
        got: "AppViewModel state yönetimini Reducer pattern'ine geçir.",
      },
    ],
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-5 h-5">
        <path d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
  },
]

function ExampleCard({ title, said, got }: { title: string; said: string; got: string }) {
  const gotLines = got.split('\n')
  return (
    <div className="rounded-xl border border-[var(--example-border)] bg-[var(--example-bg)] overflow-hidden">
      {/* Label */}
      <div className="px-4 py-2 border-b border-[var(--example-border)]">
        <span className="text-[10px] text-signal-text font-mono uppercase tracking-widest">{title}</span>
      </div>
      {/* Said */}
      <div className="px-4 py-3 border-b border-[var(--example-border)]">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-critical/60 animate-pulse" />
          <span className="text-[10px] text-[var(--subtle)] font-mono">Söylenen</span>
        </div>
        <p className="text-[13px] text-[var(--example-said)] font-mono leading-relaxed">{said}</p>
      </div>
      {/* Got */}
      <div className="px-4 py-3">
        <div className="flex items-center gap-2 mb-1.5">
          <svg viewBox="0 0 12 12" fill="none" className="w-2.5 h-2.5 text-positive" stroke="currentColor" strokeWidth="2">
            <path d="M2 6l3 3 5-5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="text-[10px] text-[var(--subtle)] font-mono">Yazılan</span>
        </div>
        <div className="text-[13px] text-[var(--heading)] leading-relaxed">
          {gotLines.map((line, i) => (
            <span key={i}>
              {line.split(/(@\S+)/g).map((part, j) =>
                part.startsWith('@') ? (
                  <span key={j} className="text-mode-general font-mono text-xs">{part}</span>
                ) : (
                  <span key={j}>{part}</span>
                )
              )}
              {i < gotLines.length - 1 && <br />}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

export function ProductSection() {
  return (
    <section id="urun-detay" className="relative bg-[var(--page-bg)] py-32 overflow-hidden">
      <Container>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl mx-auto">
          {USE_CASES.map((uc, i) => (
            <FadeUp key={uc.label} delay={i * 0.12}>
              <div className="rounded-2xl border border-[var(--card-border)] bg-[var(--card-bg)] p-7 h-full flex flex-col">
                {/* Icon + label */}
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-9 h-9 rounded-xl bg-signal/10 border border-signal/20 flex items-center justify-center text-signal-text">
                    {uc.icon}
                  </div>
                  <div>
                    <div className="text-[var(--heading)] font-semibold text-sm">{uc.label}</div>
                    <div className="text-[var(--muted)] text-xs">{uc.tagline}</div>
                  </div>
                </div>

                {/* Description */}
                <p className="text-[var(--muted)] text-sm leading-relaxed mb-5">{uc.description}</p>

                {/* Examples */}
                <div className="flex flex-col gap-3 mt-auto">
                  {uc.examples.map((ex) => (
                    <ExampleCard key={ex.title} title={ex.title} said={ex.said} got={ex.got} />
                  ))}
                </div>
              </div>
            </FadeUp>
          ))}
        </div>

        {/* Speed comparison */}
        <FadeUp delay={0.3}>
          <div className="mt-12 max-w-3xl mx-auto rounded-2xl border border-[var(--card-border)] bg-[var(--card-bg)] p-8">
            <div className="flex flex-col gap-6">

              {/* Bars */}
              <div className="flex flex-col gap-4">
                {/* Typing */}
                <div className="flex items-center gap-4">
                  <span className="text-xs text-[var(--bar-label)] w-16 text-right shrink-0">Klavye</span>
                  <div className="flex-1 h-7 rounded-lg bg-[var(--bar-track)] overflow-hidden relative">
                    <motion.div
                      className="absolute inset-y-0 left-0 rounded-lg bg-[var(--faint)]"
                      initial={{ width: 0 }}
                      whileInView={{ width: '10%' }}
                      viewport={{ once: true }}
                      transition={{ duration: 1, ease: 'easeOut', delay: 0.4 }}
                    />
                    <span className="absolute inset-y-0 left-3 flex items-center text-xs text-[var(--subtle)] font-mono">40 kelime/dk</span>
                  </div>
                </div>

                {/* Voice */}
                <div className="flex items-center gap-4">
                  <span className="text-xs text-signal-text w-16 text-right shrink-0 font-medium">Ses</span>
                  <div className="flex-1 h-7 rounded-lg bg-[var(--bar-track)] overflow-hidden relative">
                    <motion.div
                      className="absolute inset-y-0 left-0 rounded-lg bg-gradient-to-r from-signal/30 to-signal/10"
                      initial={{ width: 0 }}
                      whileInView={{ width: '100%' }}
                      viewport={{ once: true }}
                      transition={{ duration: 1.2, ease: 'easeOut', delay: 0.6 }}
                    />
                    <span className="absolute inset-y-0 left-3 flex items-center text-xs text-signal-text font-mono font-medium">400 kelime/dk</span>
                  </div>
                </div>
              </div>

              {/* Stats row */}
              <div className="flex items-center justify-center gap-8 pt-2 border-t border-[var(--divider)]">
                <div className="text-center">
                  <div className="text-2xl font-bold text-[var(--stat-value)]">10x</div>
                  <div className="text-[11px] text-[var(--subtle)]">daha hızlı</div>
                </div>
                <div className="w-px h-8 bg-[var(--divider)]" />
                <div className="text-center">
                  <div className="text-2xl font-bold text-[var(--stat-value)]">2.5<span className="text-base font-normal text-[var(--muted)]"> saat</span></div>
                  <div className="text-[11px] text-[var(--subtle)]">günlük tasarruf</div>
                </div>
              </div>

            </div>
          </div>
        </FadeUp>

      </Container>
    </section>
  )
}
