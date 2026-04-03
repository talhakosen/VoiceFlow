'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Container } from '@/components/ui/Container'
import { FadeUp } from '@/components/ui/FadeUp'
import { TESTIMONIALS } from '@/lib/constants'

export function TestimonialsSection() {
  const [current, setCurrent] = useState(0)
  const [direction, setDirection] = useState(1)

  const next = useCallback(() => {
    setDirection(1)
    setCurrent((i) => (i + 1) % TESTIMONIALS.length)
  }, [])

  const prev = useCallback(() => {
    setDirection(-1)
    setCurrent((i) => (i - 1 + TESTIMONIALS.length) % TESTIMONIALS.length)
  }, [])

  useEffect(() => {
    const interval = setInterval(next, 5000)
    return () => clearInterval(interval)
  }, [next])

  const testimonial = TESTIMONIALS[current]

  return (
    <section id="referanslar" className="section-padding bg-ink">
      <Container size="lg">
        <div className="text-center mb-16">
          <FadeUp>
            <span className="section-label text-brand-blue">Müşteri Hikayeleri</span>
          </FadeUp>
          <FadeUp delay={0.1}>
            <h2 className="text-4xl lg:text-5xl font-bold text-white tracking-tight mb-4">
              Kurumlar ne diyor?
            </h2>
          </FadeUp>
        </div>

        <div className="relative max-w-3xl mx-auto">
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={current}
              custom={direction}
              initial={{ opacity: 0, x: direction * 32 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: direction * -32 }}
              transition={{ duration: 0.38, ease: 'easeInOut' }}
            >
              <div className="bg-ink-2 rounded-card border border-white/[0.08] p-8 lg:p-12 relative overflow-hidden">
                {/* Large decorative quote mark */}
                <span
                  className="font-mono text-[96px] leading-none text-brand-blue/10 absolute -top-2 left-6 select-none pointer-events-none"
                  aria-hidden="true"
                >
                  &ldquo;
                </span>

                <blockquote className="relative text-xl lg:text-[22px] font-medium text-white/80 leading-relaxed mt-6 mb-8">
                  {testimonial.quote}
                </blockquote>

                <div className="flex items-center gap-4 pt-6 border-t border-white/[0.07]">
                  <div className="w-11 h-11 rounded-full bg-blue-gradient flex items-center justify-center text-white font-bold text-sm shrink-0 font-mono">
                    {testimonial.avatar}
                  </div>
                  <div>
                    <div className="font-semibold text-white text-sm">
                      {testimonial.author}
                    </div>
                    <div className="text-xs text-white/35 mt-0.5 font-mono">
                      {testimonial.title} · {testimonial.company}
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </AnimatePresence>

          {/* Navigation */}
          <div className="flex items-center justify-center gap-4 mt-8">
            <button
              onClick={prev}
              aria-label="Önceki"
              className="w-9 h-9 rounded-full border border-white/[0.09] hover:border-brand-blue/35 hover:bg-brand-blue/5 transition-all flex items-center justify-center text-white/35 hover:text-brand-blue-light"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                strokeWidth="2"
                stroke="currentColor"
                className="w-4 h-4"
              >
                <path d="m15 18-6-6 6-6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>

            <div className="flex gap-2 items-center">
              {TESTIMONIALS.map((_, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setDirection(i > current ? 1 : -1)
                    setCurrent(i)
                  }}
                  aria-label={`Yorum ${i + 1}`}
                  className={`transition-all duration-300 rounded-full ${
                    i === current
                      ? 'w-6 h-2 bg-brand-blue'
                      : 'w-2 h-2 bg-white/[0.14] hover:bg-white/[0.28]'
                  }`}
                />
              ))}
            </div>

            <button
              onClick={next}
              aria-label="Sonraki"
              className="w-9 h-9 rounded-full border border-white/[0.09] hover:border-brand-blue/35 hover:bg-brand-blue/5 transition-all flex items-center justify-center text-white/35 hover:text-brand-blue-light"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                strokeWidth="2"
                stroke="currentColor"
                className="w-4 h-4"
              >
                <path d="m9 18 6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        </div>
      </Container>
    </section>
  )
}
