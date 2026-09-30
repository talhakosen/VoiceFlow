'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/Button'
import { HERO } from '@/lib/constants'

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

const CORRECTIONS = [
  { wrong: 'rays kontisen',  type: 'fix',    label: 'Terim düzeltildi',        result: 'race condition'    },
  { wrong: 'ondört',         type: 'format', label: 'Saat formatlandı',        result: '14:00'             },
  { wrong: 'yani yani',      type: 'remove', label: 'Dolgu söz kaldırıldı',    result: null                },
  { wrong: 'ise başlayan',   type: 'spell',  label: 'Yazım düzeltildi',        result: 'işe başlayan'      },
  { wrong: 'apivumodel',     type: 'fix',    label: 'Terim düzeltildi',        result: 'AppViewModel'      },
  { wrong: 'kdv beyanname',  type: 'format', label: 'Büyük harf eklendi',      result: 'KDV Beyannamesi'   },
  { wrong: 'olustur',        type: 'spell',  label: 'Yazım düzeltildi',        result: 'oluştur'           },
  { wrong: 'doker kubernet', type: 'fix',    label: 'Terim düzeltildi',        result: 'Docker Kubernetes' },
  { wrong: 'auth servis',    type: 'inject', label: 'Referans inject edildi',  result: '@AuthService'      },
] as const

type Correction = typeof CORRECTIONS[number]

function WaveformBars() {
  return (
    <div className="flex items-center gap-[3px]">
      {[5, 9, 15, 8, 12, 18, 10, 14, 7, 11, 16, 9, 6].map((h, i) => (
        <motion.span
          key={i}
          className="w-[3px] rounded-full dark:bg-white bg-white inline-block"
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
          <span className="opacity-15"> · </span>
        </span>
      ))}
    </>
  )
  return (
    <div className={`flex whitespace-nowrap animate-marquee-left font-mono text-sm ${
      bright
        ? 'text-text dark:text-white'
        : 'text-text-muted'
    }`}>
      <span>{content}</span>
      <span>{content}</span>
    </div>
  )
}

const LINE_COLOR: Record<string, string> = {
  fix:    'bg-mode-office',
  remove: 'bg-critical',
  format: 'bg-signal',
  spell:  'bg-caution',
  inject: 'bg-mode-general',
}

function WrongBadge({ corr }: { corr: Correction }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.22 }}
      className="relative flex items-center text-sm font-mono text-text-muted dark:text-text-muted"
    >
      {corr.wrong}
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
      className="whitespace-nowrap flex items-center gap-s-2 bg-positive/10 border border-positive/30 text-positive text-data-s font-mono px-s-3 py-s-1 rounded-full"
    >
      <svg viewBox="0 0 12 12" fill="none" className="w-3 h-3 shrink-0" stroke="currentColor" strokeWidth="2">
        <path d="M2 6l3 3 5-5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span>{corr.label}</span>
      {corr.result && (
        <>
          <span className="opacity-30 mx-0.5">·</span>
          <span className="text-text-muted dark:text-text-muted line-through text-[10px]">{corr.wrong}</span>
          <span className="opacity-50 mx-0.5">→</span>
          <span className={`font-semibold ${corr.type === 'inject' ? 'text-mode-general dark:text-mode-general' : 'text-positive dark:text-positive'}`}>
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
      className="relative min-h-screen flex flex-col justify-center items-center bg-ground dark:bg-ground overflow-hidden pt-[var(--navbar-height)]"
    >
      {/* Glow */}

      {/* Başlık + CTA */}
      <div className="relative z-10 text-center px-6 w-full max-w-4xl mx-auto flex flex-col items-center">
        <motion.h1
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="text-6xl sm:text-7xl lg:text-8xl font-bold text-text dark:text-white leading-[1.05] tracking-tight mb-6 whitespace-pre-line"
        >
          {HERO.tagline}
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="text-lg sm:text-xl text-text-muted dark:text-text-muted mb-10 sm:whitespace-nowrap max-w-xs sm:max-w-none"
        >
          {HERO.subtext}
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.28 }}
          className="mb-16"
        >
          <Button
            size="lg"
            variant="primary"
            className="text-base px-10"
            onClick={() => {
              const el = document.getElementById('demo')
              if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
            }}
          >
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
              <div className="absolute right-0 inset-y-0 w-24 bg-gradient-to-r from-transparent to-ground dark:to-ground z-10 pointer-events-none" />
              <Strip text={RAW_TEXT} bright={false} />
            </div>

            {/* Sağ: FIX */}
            <div className="absolute inset-y-0 left-1/2 right-0 overflow-hidden flex items-center">
              <div className="absolute left-0 inset-y-0 w-20 bg-gradient-to-r from-ground dark:from-ground to-transparent z-10 pointer-events-none" />
              <div className="absolute inset-0 bg-black/[0.04] dark:bg-control border-t border-b border-black/[0.07] dark:border-line" />
              <div className="relative">
                <Strip text={FIX_TEXT} bright={true} />
              </div>
            </div>

          </div>

          {/* Waveform pill */}
          <div className="absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2 z-20">
            <div className="flex items-center gap-3 bg-surface-raised dark:bg-[#0c1228] border-2 border-line rounded-2xl px-5 py-2.5 shadow-[0_0_24px_rgba(59,130,246,0.3)]">
              <span className="w-2.5 h-2.5 rounded-full bg-critical animate-pulse shrink-0" />
              <WaveformBars />
            </div>
          </div>
        </div>

        {/* Pipeline — 3 node connected by gradient lines */}
        <div className="relative flex items-start justify-center mt-5 px-4 sm:px-12 max-w-xl mx-auto">

          {/* Connecting lines (behind nodes) */}
          <div className="absolute top-3 left-[calc(16.67%+12px)] right-[calc(16.67%+12px)] flex z-0">
            <div className="flex-1 h-px bg-gradient-to-r from-line-strong/60 dark:from-white/10 to-signal/40" />
            <div className="flex-1 h-px bg-gradient-to-r from-signal/40 to-line-strong/60 dark:to-white/15" />
          </div>

          {/* Node 1 — Ham ses */}
          <div className="relative z-10 flex flex-col items-center flex-1">
            <div className="w-6 h-6 rounded-full bg-control dark:bg-control border border-line-strong dark:border-line flex items-center justify-center">
              <svg viewBox="0 0 16 16" fill="none" className="w-3 h-3 text-text-muted dark:text-text-muted" stroke="currentColor" strokeWidth="1.5">
                <rect x="5.5" y="1" width="5" height="8" rx="2.5" />
                <path d="M3 8a5 5 0 0 0 10 0" strokeLinecap="round" />
                <path d="M8 13v2" strokeLinecap="round" />
              </svg>
            </div>
            <span className="text-[11px] text-text-muted dark:text-text-muted mt-1.5 font-medium">Ham ses</span>
          </div>

          {/* Node 2 — Özel model (hero node) */}
          <div className="relative z-10 flex flex-col items-center flex-1">
            <div className="w-6 h-6 rounded-full bg-signal/15 dark:bg-signal/20 border border-signal/40 flex items-center justify-center">
              <svg viewBox="0 0 12 12" fill="currentColor" className="w-2.5 h-2.5 text-signal-text">
                <path d="M6 0l1.5 3.5L11 5l-3 2.5L9 11l-3-2-3 2 1-3.5L1 5l3.5-1.5z"/>
              </svg>
            </div>
            <span className="text-[11px] text-signal-text font-semibold mt-1.5">Özel model</span>
            <span className="text-[9px] text-text-muted dark:text-text-muted mt-0.5 font-mono">300K+ Türkçe ses</span>
          </div>

          {/* Node 3 — İşlenmiş yazı */}
          <div className="relative z-10 flex flex-col items-center flex-1">
            <div className="w-6 h-6 rounded-full bg-positive dark:bg-positive/10 border border-positive/60 dark:border-positive/25 flex items-center justify-center">
              <svg viewBox="0 0 16 16" fill="none" className="w-3 h-3 text-positive dark:text-positive" stroke="currentColor" strokeWidth="1.5">
                <path d="M3 4.5h10M3 8h7M3 11.5h5" strokeLinecap="round" />
              </svg>
            </div>
            <span className="text-[11px] text-text-muted dark:text-text-muted mt-1.5 font-medium">İşlenmiş yazı</span>
          </div>

        </div>
      </motion.div>

    </section>
  )
}
