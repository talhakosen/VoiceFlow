'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/Button'
import { HERO, TRUSTED_LOGOS } from '@/lib/constants'

// Plain continuous text streams — left: broken input, right: corrected output
// No per-item sync needed; pills explain the corrections
const RAW_TEXT =
  'bütçe revizyon ondört perşembe · rays kontisen sorunu düzelt · yeni ise başlayan onboarding takvim · ' +
  'kdv beyanname son gün haber ver · mayıs sosyal medya takvim yap · apivumodel tıken rıfres güncelle · ' +
  'performans formaları bu ay yolla · yeni ürün basın bülteni yaz · doker kubernet konfig deploy güncelle · ' +
  'q4 raporu pazartesiye hazırla bitti · sosyal medya takvim olustur · bütçe perşembe ondort revizyon ·'

const FIX_TEXT =
  'Bütçe revizyonu Perşembe saat 14:00. · Race condition sorununu düzelt. · Yeni işe başlayan onboarding takvimini hazırla. · ' +
  'KDV beyannamesi son gün, haber verin. · Mayıs sosyal medya takvimini oluştur. · AppViewModel token refresh güncelle. · ' +
  'Performans formlarını bu ay gönderin. · Yeni ürün lansmanı için basın bülteni yaz. · Docker Kubernetes config deploy güncelle. · ' +
  'Q4 raporu pazartesiye hazırlandı. · Sosyal medya takvimini Mayıs için oluştur. · Bütçe revizyonu Perşembe saat 14:00. ·'

// type:
//   'fix'    — wrong term replaced (purple strikethrough)
//   'remove' — filler word deleted (red strikethrough, no result)
//   'format' — number/capitalization reformatted (amber underline pulse)
//   'spell'  — spelling fixed (orange squiggle)
const CORRECTIONS = [
  { wrong: 'rays kontisen',  type: 'fix',    label: 'Terim düzeltildi',        result: 'race condition'   },
  { wrong: 'ondört',         type: 'format', label: 'Saat formatlandı',        result: '14:00'            },
  { wrong: 'yani yani',      type: 'remove', label: 'Dolgu söz kaldırıldı',    result: null               },
  { wrong: 'ise başlayan',   type: 'spell',  label: 'Yazım düzeltildi',        result: 'işe başlayan'     },
  { wrong: 'apivumodel',     type: 'fix',    label: 'Terim düzeltildi',        result: 'AppViewModel'     },
  { wrong: 'kdv beyanname',  type: 'format', label: 'Büyük harf eklendi',      result: 'KDV Beyannamesi'  },
  { wrong: 'olustur',        type: 'spell',  label: 'Yazım düzeltildi',        result: 'oluştur'          },
  { wrong: 'doker kubernet', type: 'fix',    label: 'Terim düzeltildi',        result: 'Docker Kubernetes'},
  { wrong: 'auth servis',   type: 'inject', label: 'Referans inject edildi',  result: '@AuthService'     },
] as const

type Correction = typeof CORRECTIONS[number]

function WaveformBars() {
  return (
    <div className="flex items-center gap-[3px]">
      {[5, 9, 15, 8, 12, 18, 10, 14, 7, 11, 16, 9, 6].map((h, i) => (
        <motion.span
          key={i}
          className="w-[3px] rounded-full bg-white inline-block"
          animate={{ scaleY: [0.3, 1, 0.5, 1.1, 0.4, 1] }}
          transition={{ duration: 1.1 + i * 0.07, repeat: Infinity, ease: 'easeInOut', delay: i * 0.06 }}
          style={{ height: h }}
        />
      ))}
    </div>
  )
}

function Strip({ text, bright }: { text: string; bright: boolean }) {
  const parts = text.split(' · ')
  const content = (
    <>
      {parts.map((part, i) => (
        <span key={i}>
          {part}
          <span className="text-white/15"> · </span>
        </span>
      ))}
    </>
  )
  return (
    <div className={`flex whitespace-nowrap animate-marquee-left font-mono text-sm ${bright ? 'text-white' : 'text-white/55'}`}>
      <span>{content}</span>
      <span>{content}</span>
    </div>
  )
}

// Strikethrough line color by error type
const LINE_COLOR: Record<string, string> = {
  fix:    'bg-purple-400',
  remove: 'bg-red-400',
  format: 'bg-amber-400',
  spell:  'bg-orange-400',
  inject: 'bg-cyan-400',
}

function WrongBadge({ corr }: { corr: Correction }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.22 }}
      className="relative flex items-center text-sm font-mono text-white/55"
    >
      {corr.wrong}
      {/* Strikethrough line grows left-to-right */}
      <motion.span
        className={`absolute left-0 top-1/2 h-[1.5px] origin-left ${LINE_COLOR[corr.type]}`}
        style={{ width: '100%' }}
        initial={{ scaleX: 0 }}
        animate={{ scaleX: 1 }}
        transition={{ delay: 0.45, duration: 0.35, ease: 'easeInOut' }}
      />
    </motion.div>
  )
}

function ActionBadge({ corr }: { corr: Correction }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -6, scale: 0.95 }}
      transition={{ duration: 0.22 }}
      className="whitespace-nowrap flex items-center gap-1.5 bg-[#0f2318] border border-green-500/40 text-green-400 text-[11px] font-medium px-3 py-1 rounded-full shadow-lg"
    >
      <svg viewBox="0 0 12 12" fill="none" className="w-3 h-3 shrink-0" stroke="currentColor" strokeWidth="2">
        <path d="M2 6l3 3 5-5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span>{corr.label}</span>
      {/* Show before→after if result exists */}
      {corr.result && (
        <>
          <span className="text-green-400/30 mx-0.5">·</span>
          <span className="text-white/40 line-through text-[10px]">{corr.wrong}</span>
          <span className="text-green-400/50 mx-0.5">→</span>
          <span className={`font-semibold ${corr.type === 'inject' ? 'text-cyan-300' : 'text-green-300'}`}>
            {corr.result}
          </span>
        </>
      )}
    </motion.div>
  )
}

type Phase = 'wrong' | 'action'

export function HeroSection() {
  const [corrIdx, setCorrIdx] = useState(0)
  const [phase, setPhase] = useState<Phase>('wrong')

  useEffect(() => {
    const duration = phase === 'wrong' ? 1500 : 1800
    const t = setTimeout(() => {
      if (phase === 'wrong') {
        setPhase('action')
      } else {
        setPhase('wrong')
        setCorrIdx(i => (i + 1) % CORRECTIONS.length)
      }
    }, duration)
    return () => clearTimeout(t)
  }, [phase, corrIdx])

  return (
    <section
      id="urun"
      className="relative min-h-screen flex flex-col justify-center items-center bg-brand-navy overflow-hidden pt-[var(--navbar-height)]"
    >
      <div className="absolute inset-0 bg-hero-gradient" />
      <div className="glow-orb w-[700px] h-[700px] bg-brand-blue/8 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />

      {/* Başlık + CTA */}
      <div className="relative z-10 text-center px-6 w-full max-w-4xl mx-auto flex flex-col items-center">
        <motion.h1
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="text-6xl sm:text-7xl lg:text-8xl font-bold text-white leading-[1.05] tracking-tight mb-6 whitespace-pre-line"
        >
          {HERO.tagline}
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="text-lg sm:text-xl text-text-muted mb-10 max-w-md"
        >
          {HERO.subtext}
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.28 }}
          className="mb-16"
        >
          <Button size="lg" variant="primary" className="text-base px-10">
            {HERO.ctaPrimary}
          </Button>
        </motion.div>
      </div>

      {/* DÖNÜŞÜM ŞERİDİ */}
      <motion.div
        className="relative z-10 w-full mb-5"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.5 }}
      >
        {/* Two-phase badge */}
        <div className="flex justify-center mb-2 h-8">
          <AnimatePresence mode="wait">
            {phase === 'wrong' ? (
              <WrongBadge key={`wrong-${corrIdx}`} corr={CORRECTIONS[corrIdx]} />
            ) : (
              <ActionBadge key={`action-${corrIdx}`} corr={CORRECTIONS[corrIdx]} />
            )}
          </AnimatePresence>
        </div>

        {/* Strip row + waveform pill */}
        <div className="relative">
          <div className="relative flex items-center overflow-hidden" style={{ height: 56 }}>

            {/* Sol: RAW */}
            <div className="absolute inset-y-0 left-0 right-1/2 overflow-hidden flex items-center">
              <div className="absolute right-0 inset-y-0 w-24 bg-gradient-to-r from-transparent to-brand-navy z-10 pointer-events-none" />
              <Strip text={RAW_TEXT} bright={false} />
            </div>

            {/* Sağ: FIX */}
            <div className="absolute inset-y-0 left-1/2 right-0 overflow-hidden flex items-center">
              <div className="absolute left-0 inset-y-0 w-20 bg-gradient-to-r from-brand-navy to-transparent z-10 pointer-events-none" />
              <div className="absolute inset-0 bg-white/[0.06] border-t border-b border-white/[0.10]" />
              <div className="relative">
                <Strip text={FIX_TEXT} bright={true} />
              </div>
            </div>

          </div>

          {/* Waveform pill — outside overflow-hidden */}
          <div className="absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2 z-20">
            <div className="flex items-center gap-3 bg-[#0c1228] border-2 border-white/20 rounded-2xl px-5 py-2.5 shadow-[0_0_24px_rgba(59,130,246,0.3)]">
              <span className="w-2.5 h-2.5 rounded-full bg-red-400 animate-pulse shrink-0" />
              <WaveformBars />
            </div>
          </div>
        </div>

        {/* Etiket */}
        <div className="flex items-center justify-center gap-6 mt-3">
          <span className="text-xs text-white/25 font-mono">Ham ses</span>
          <span className="text-xs text-white/15">→</span>
          <span className="text-xs text-white/40">300K+ Türkçe ses ile eğitilmiş özel model</span>
        </div>
      </motion.div>

      {/* Güvenilen kurumlar */}
      <motion.div
        className="relative z-10 text-center px-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1, delay: 0.6 }}
      >
        <p className="text-xs text-text-muted/40 uppercase tracking-widest mb-4">
          {HERO.trustedBy}
        </p>
        <div className="flex flex-wrap justify-center gap-x-8 gap-y-2">
          {TRUSTED_LOGOS.map((logo) => (
            <span key={logo} className="text-sm font-semibold text-white/15 tracking-wide">
              {logo}
            </span>
          ))}
        </div>
      </motion.div>
    </section>
  )
}
