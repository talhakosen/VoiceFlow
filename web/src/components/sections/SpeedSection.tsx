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
        <span className="font-medium text-text-muted">{label}</span>
        <span className="font-bold text-white font-mono tabular-nums">{wpm} kelime/dk</span>
      </div>
      <div className="h-1.5 bg-control rounded-full overflow-hidden">
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
    <section id="ozellikler" className="section-padding bg-ground">
      <Container>
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left: copy */}
          <div>
            <FadeUp>
              <span className="section-label">Verimlilik</span>
            </FadeUp>
            <FadeUp delay={0.1}>
              <h2 className="text-4xl lg:text-5xl font-bold text-white leading-tight tracking-tight mb-6">
                Klavyeden 10x
                <br />
                <span className="text-signal-text">daha hızlı.</span>
              </h2>
            </FadeUp>
            <FadeUp delay={0.2}>
              <p className="text-lg text-text-muted leading-relaxed mb-10">
                Ortalama insan dakikada 40 kelime yazar. Konuşarak dakikada 400
                kelimeye ulaşın. Günde 2.5 saat geri kazanın.
              </p>
            </FadeUp>

            {/* Comparison table */}
            <FadeUp delay={0.3}>
              <div className="rounded-lg border border-line overflow-hidden">
                <div className="grid grid-cols-3 border-b border-line bg-control/40 px-4 py-3">
                  <span className="section-label text-text-muted mb-0">Özellik</span>
                  <span className="section-label text-text-muted mb-0 text-center">Klavye</span>
                  <span className="section-label mb-0 text-center">VoiceFlow</span>
                </div>
                {COMPARISON_ROWS.map((row, i) => (
                  <div
                    key={row.feature}
                    className={`grid grid-cols-3 px-4 py-3.5 text-sm ${
                      i !== COMPARISON_ROWS.length - 1
                        ? 'border-b border-line'
                        : ''
                    }`}
                  >
                    <span className="text-text-muted font-medium text-xs">{row.feature}</span>
                    <span className="text-center text-text-muted text-xs">{row.keyboard}</span>
                    <span className="text-center text-signal-text font-semibold text-xs">{row.voice}</span>
                  </div>
                ))}
              </div>
            </FadeUp>
          </div>

          {/* Right: speed bars */}
          <div ref={ref}>
            <FadeUp delay={0.2}>
              <div className="rounded-lg bg-surface p-8 border border-line">
                <h3 className="font-bold text-white mb-8 text-lg">
                  İçerik Üretim Hızı Karşılaştırması
                </h3>
                <div className="space-y-7">
                  <SpeedBar
                    label="Klavye Yazma"
                    wpm={40}
                    maxWpm={400}
                    color="bg-line-strong/60"
                    delay={0.3}
                    inView={inView}
                  />
                  <SpeedBar
                    label="VoiceFlow"
                    wpm={400}
                    maxWpm={400}
                    color="bg-signal"
                    delay={0.5}
                    inView={inView}
                  />
                </div>

                <div className="mt-10 pt-6 border-t border-line grid grid-cols-3 gap-4">
                  {[
                    { value: '10x', label: 'Daha Hızlı' },
                    { value: '2.5s', label: 'Günlük Tasarruf' },
                    { value: '98.7%', label: 'Doğruluk' },
                  ].map((item) => (
                    <div key={item.label} className="text-center">
                      <div className="text-2xl font-bold text-signal-text font-mono tabular-nums">
                        {item.value}
                      </div>
                      <div className="section-label text-text-muted mt-1 mb-0">{item.label}</div>
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
