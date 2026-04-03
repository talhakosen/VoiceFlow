'use client'

import { useRef } from 'react'
import { motion, useInView } from 'framer-motion'
import { Container } from '@/components/ui/Container'
import { FadeUp } from '@/components/ui/FadeUp'
import { COMPARISON_ROWS } from '@/lib/constants'

function SpeedBar({
  label,
  wpm,
  maxWpm,
  color,
  delay,
  inView,
}: {
  label: string
  wpm: number
  maxWpm: number
  color: string
  delay: number
  inView: boolean
}) {
  const pct = (wpm / maxWpm) * 100

  return (
    <div>
      <div className="flex justify-between text-sm mb-2.5">
        <span className="font-medium text-white/60">{label}</span>
        <span className="font-bold text-white font-mono tabular-nums">{wpm} kelime/dk</span>
      </div>
      <div className="h-1.5 bg-white/[0.07] rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={inView ? { width: `${pct}%` } : { width: 0 }}
          transition={{ duration: 1.2, delay, ease: [0.33, 1, 0.68, 1] }}
          className={`h-full rounded-full ${color}`}
        />
      </div>
    </div>
  )
}

export function SpeedSection() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, amount: 0.3 })

  return (
    <section id="ozellikler" className="section-padding bg-ink">
      <Container>
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left: copy */}
          <div>
            <FadeUp>
              <span className="section-label text-brand-blue">Verimlilik</span>
            </FadeUp>
            <FadeUp delay={0.1}>
              <h2 className="text-4xl lg:text-5xl font-bold text-white leading-tight tracking-tight mb-6">
                Klavyeden 10x
                <br />
                <span className="text-brand-blue-light">daha hızlı.</span>
              </h2>
            </FadeUp>
            <FadeUp delay={0.2}>
              <p className="text-lg text-white/45 leading-relaxed mb-10">
                Ortalama insan dakikada 40 kelime yazar. Konuşarak dakikada 400
                kelimeye ulaşın. Günde 2.5 saat geri kazanın.
              </p>
            </FadeUp>

            {/* Comparison table */}
            <FadeUp delay={0.3}>
              <div className="rounded-card border border-white/[0.08] overflow-hidden">
                <div className="grid grid-cols-3 border-b border-white/[0.06] bg-white/[0.03] px-4 py-3">
                  <span className="section-label text-white/25 mb-0">Özellik</span>
                  <span className="section-label text-white/25 mb-0 text-center">Klavye</span>
                  <span className="section-label text-brand-blue mb-0 text-center">VoiceFlow</span>
                </div>
                {COMPARISON_ROWS.map((row, i) => (
                  <div
                    key={row.feature}
                    className={`grid grid-cols-3 px-4 py-3.5 text-sm ${
                      i !== COMPARISON_ROWS.length - 1
                        ? 'border-b border-white/[0.05]'
                        : ''
                    }`}
                  >
                    <span className="text-white/55 font-medium text-xs">{row.feature}</span>
                    <span className="text-center text-white/25 text-xs">{row.keyboard}</span>
                    <span className="text-center text-brand-blue-light font-semibold text-xs">{row.voice}</span>
                  </div>
                ))}
              </div>
            </FadeUp>
          </div>

          {/* Right: speed bars */}
          <div ref={ref}>
            <FadeUp delay={0.2}>
              <div className="rounded-card bg-ink-2 p-8 border border-white/[0.08]">
                <h3 className="font-bold text-white mb-8 text-lg">
                  İçerik Üretim Hızı Karşılaştırması
                </h3>
                <div className="space-y-7">
                  <SpeedBar
                    label="Klavye Yazma"
                    wpm={40}
                    maxWpm={400}
                    color="bg-white/[0.18]"
                    delay={0.3}
                    inView={inView}
                  />
                  <SpeedBar
                    label="VoiceFlow"
                    wpm={400}
                    maxWpm={400}
                    color="bg-blue-gradient"
                    delay={0.5}
                    inView={inView}
                  />
                </div>

                <div className="mt-10 pt-6 border-t border-white/[0.07] grid grid-cols-3 gap-4">
                  {[
                    { value: '10x', label: 'Daha Hızlı' },
                    { value: '2.5s', label: 'Günlük Tasarruf' },
                    { value: '98.7%', label: 'Doğruluk' },
                  ].map((item) => (
                    <div key={item.label} className="text-center">
                      <div className="text-2xl font-bold text-brand-blue font-mono tabular-nums">
                        {item.value}
                      </div>
                      <div className="section-label text-white/25 mt-1 mb-0">{item.label}</div>
                    </div>
                  ))}
                </div>
              </div>
            </FadeUp>
          </div>
        </div>
      </Container>
    </section>
  )
}
