'use client'

import { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { DEMO_STRIP } from '@/lib/constants'

function WaveformBars() {
  return (
    <div className="flex items-center gap-[3px] h-5">
      {[4, 8, 13, 7, 11, 15, 9, 13, 6, 10, 14, 8, 5].map((h, i) => (
        <motion.span
          key={i}
          className="w-[3px] rounded-full bg-brand-blue-light/80"
          animate={{ height: [h * 0.5, h, h * 0.7, h * 1.1, h * 0.6, h] }}
          transition={{
            duration: 1.1 + i * 0.07,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: i * 0.06,
          }}
          style={{ height: h }}
        />
      ))}
    </div>
  )
}

export function DemoStripSection() {
  const [index, setIndex] = useState(0)
  const [phase, setPhase] = useState<'raw' | 'corrected'>('raw')

  const advance = useCallback(() => {
    setPhase('raw')
    setIndex((i) => (i + 1) % DEMO_STRIP.examples.length)
  }, [])

  useEffect(() => {
    if (phase === 'raw') {
      const t = setTimeout(() => setPhase('corrected'), 2800)
      return () => clearTimeout(t)
    }
    if (phase === 'corrected') {
      const t = setTimeout(advance, 3200)
      return () => clearTimeout(t)
    }
  }, [phase, advance])

  const example = DEMO_STRIP.examples[index]

  return (
    <section className="py-0 bg-brand-navy">
      {/* Full-width strip */}
      <div className="w-full border-y border-white/[0.08] bg-white/[0.03] backdrop-blur-sm py-5 overflow-hidden">
        <div className="max-w-5xl mx-auto px-6 flex items-center gap-5">

          {/* Left: pill with waveform */}
          <div className="shrink-0 flex items-center gap-3 bg-white/[0.07] border border-white/[0.12] rounded-pill px-4 py-2.5">
            <span className="w-2 h-2 rounded-full bg-red-400 animate-pulse shrink-0" />
            <WaveformBars />
          </div>

          {/* Arrow */}
          <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4 text-white/20 shrink-0" strokeWidth="1.5" stroke="currentColor">
            <path d="M5 12h14m-7-7 7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
          </svg>

          {/* Context label */}
          <span className="shrink-0 text-xs font-semibold text-brand-blue-light/70 uppercase tracking-widest hidden sm:block">
            {example.context}
          </span>

          {/* Text */}
          <div className="flex-1 min-w-0 overflow-hidden">
            <AnimatePresence mode="wait">
              <motion.p
                key={`${index}-${phase}`}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.3 }}
                className={`text-sm truncate ${
                  phase === 'raw'
                    ? 'text-text-muted font-mono'
                    : 'text-white font-sans'
                }`}
              >
                {phase === 'raw' ? example.raw : example.corrected}
              </motion.p>
            </AnimatePresence>
          </div>

          {/* Status badge */}
          <div className="shrink-0 hidden md:block">
            <AnimatePresence mode="wait">
              {phase === 'raw' ? (
                <motion.span
                  key="recording"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="text-xs text-text-muted/60"
                >
                  Dinleniyor…
                </motion.span>
              ) : (
                <motion.span
                  key="done"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center gap-1.5 text-xs text-accent-green"
                >
                  <svg viewBox="0 0 24 24" fill="none" className="w-3.5 h-3.5" strokeWidth="2.5" stroke="currentColor">
                    <path d="M20 6 9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  Düzeltildi
                </motion.span>
              )}
            </AnimatePresence>
          </div>

          {/* Progress dots */}
          <div className="shrink-0 flex items-center gap-1.5">
            {DEMO_STRIP.examples.map((_, i) => (
              <span
                key={i}
                className={`rounded-full transition-all duration-300 ${
                  i === index
                    ? 'w-4 h-1.5 bg-brand-blue'
                    : 'w-1.5 h-1.5 bg-white/15'
                }`}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
