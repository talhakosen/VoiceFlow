'use client'

import { motion, useScroll, useTransform } from 'framer-motion'
import { Container } from '@/components/ui/Container'
import { useTheme } from '@/components/ThemeProvider'

function ThemeToggle() {
  const { theme, toggle } = useTheme()

  return (
    <button
      onClick={toggle}
      aria-label={theme === 'dark' ? 'Açık temaya geç' : 'Koyu temaya geç'}
      className="w-9 h-9 rounded-full border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 flex items-center justify-center text-slate-500 dark:text-white/50 hover:text-slate-900 dark:hover:text-white hover:border-slate-300 dark:hover:border-white/20 transition-colors shadow-sm"
    >
      {theme === 'dark' ? (
        /* Sun */
        <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
          <path d="M10 2a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0v-1.5A.75.75 0 0 1 10 2Zm0 13a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0v-1.5A.75.75 0 0 1 10 15Zm0-8a3 3 0 1 0 0 6 3 3 0 0 0 0-6Zm5.657-1.596a.75.75 0 1 0-1.06-1.06l-1.061 1.06a.75.75 0 0 0 1.06 1.06l1.06-1.06Zm-9.193 9.192a.75.75 0 1 0-1.06-1.06l-1.06 1.06a.75.75 0 0 0 1.06 1.06l1.06-1.06ZM18 10a.75.75 0 0 1-.75.75h-1.5a.75.75 0 0 1 0-1.5h1.5A.75.75 0 0 1 18 10ZM5 10a.75.75 0 0 1-.75.75h-1.5a.75.75 0 0 1 0-1.5h1.5A.75.75 0 0 1 5 10Zm9.596 5.657a.75.75 0 0 0 1.06-1.06l-1.06-1.061a.75.75 0 1 0-1.06 1.06l1.06 1.06ZM5.404 6.464a.75.75 0 0 0 1.06-1.06l-1.06-1.06a.75.75 0 1 0-1.06 1.06l1.06 1.06Z" />
        </svg>
      ) : (
        /* Moon */
        <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
          <path fillRule="evenodd" d="M7.455 2.004a.75.75 0 0 1 .26.77 7 7 0 0 0 9.958 7.967.75.75 0 0 1 1.067.853A8.5 8.5 0 1 1 6.647 1.921a.75.75 0 0 1 .808.083Z" clipRule="evenodd" />
        </svg>
      )}
    </button>
  )
}

export function Navbar() {
  const { scrollY } = useScroll()

  const navBg = useTransform(scrollY, [0, 80], ['rgba(7,8,16,0)', 'rgba(7,8,16,0.92)'])
  const navBorder = useTransform(scrollY, [0, 80], ['rgba(255,255,255,0)', 'rgba(255,255,255,0.07)'])
  const navBlur = useTransform(scrollY, [0, 80], ['blur(0px)', 'blur(20px)'])

  return (
    <motion.header
      style={{ backgroundColor: navBg, borderColor: navBorder }}
      className="fixed top-0 left-0 right-0 z-50 border-b"
    >
      <motion.div
        style={{ backdropFilter: navBlur, WebkitBackdropFilter: navBlur }}
        className="absolute inset-0 pointer-events-none"
      />
      <Container className="relative">
        <div className="flex items-center justify-between h-[var(--navbar-height)]">
          <a
            href="#"
            className="flex items-center gap-2.5 group"
            onClick={(e) => { e.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }) }}
          >
            <img
              src="/app-icon.png"
              alt=""
              className="h-8 w-8 transition-opacity duration-200 group-hover:opacity-75"
            />
            <span className="font-bold text-lg tracking-tight text-slate-900 dark:text-white transition-opacity duration-200 group-hover:opacity-75">
              VoiceFlow
            </span>
          </a>

          <ThemeToggle />
        </div>
      </Container>
    </motion.header>
  )
}
