'use client'

import { motion } from 'framer-motion'
import { Container } from '@/components/ui/Container'
import { Button } from '@/components/ui/Button'

const TRUST = ['KVKK Uyumlu', 'On-Premise', 'ISO 27001']

export function ClosingSection() {
  return (
    <section id="demo" className="relative bg-[var(--page-bg-alt)] py-32 overflow-hidden">
      {/* Subtle glow */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-brand-blue/5 blur-[80px] rounded-full pointer-events-none" />

      <Container size="sm">
        <motion.div
          className="flex flex-col items-center text-center gap-8"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        >
          <h2 className="text-4xl sm:text-5xl font-bold text-[var(--heading)] leading-tight tracking-tight">
            Kurumunuz için özel<br />
            <span className="text-[var(--muted)]">demo planlayalım.</span>
          </h2>

          <p className="text-[var(--muted)] text-lg max-w-sm leading-relaxed">
            15 dakikada kurulumu gösteririz. Verileriniz kurumunuzdan ayrılmaz.
          </p>

          <a href="mailto:demo@voiceflow.ai">
            <Button size="lg" variant="primary" className="text-base px-12">
              Demo Talep Edin
            </Button>
          </a>

          {/* Trust badges */}
          <div className="flex items-center gap-2 pt-2">
            {TRUST.map((t, i) => (
              <div key={t} className="flex items-center gap-2">
                {i > 0 && <span className="w-px h-3 bg-[var(--divider)]" />}
                <span className="text-xs text-[var(--subtle)] tracking-wide">{t}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </Container>
    </section>
  )
}
