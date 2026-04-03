'use client'

import { useState, useEffect } from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Container } from '@/components/ui/Container'
import { Button } from '@/components/ui/Button'
import { NAV_LINKS } from '@/lib/constants'

export function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [activeSection, setActiveSection] = useState('')
  const { scrollY } = useScroll()

  // Always dark — transitions from transparent to deep ink
  const navBg = useTransform(
    scrollY,
    [0, 80],
    ['rgba(7,8,16,0)', 'rgba(7,8,16,0.92)']
  )
  const navBorder = useTransform(
    scrollY,
    [0, 80],
    ['rgba(255,255,255,0)', 'rgba(255,255,255,0.07)']
  )
  const navBlur = useTransform(scrollY, [0, 80], ['blur(0px)', 'blur(20px)'])

  useEffect(() => {
    const handleScroll = () => {
      const sections = NAV_LINKS.map((l) => l.href.replace('#', ''))
      for (const id of [...sections].reverse()) {
        const el = document.getElementById(id)
        if (el) {
          const rect = el.getBoundingClientRect()
          if (rect.top <= 100) {
            setActiveSection(id)
            return
          }
        }
      }
      setActiveSection('')
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const handleNavClick = (href: string) => {
    setMobileOpen(false)
    const id = href.replace('#', '')
    const el = document.getElementById(id)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  return (
    <>
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
            {/* Logo — always white on dark nav */}
            <a
              href="#"
              className="flex items-center group"
              onClick={(e) => {
                e.preventDefault()
                window.scrollTo({ top: 0, behavior: 'smooth' })
              }}
            >
              <img
                src="/text_logo.svg"
                alt="VoiceFlow"
                className="h-auto w-36 brightness-0 invert transition-opacity duration-200 group-hover:opacity-75"
              />
            </a>

            {/* Desktop Nav */}
            <nav className="hidden md:flex items-center gap-0.5">
              {NAV_LINKS.map((link) => {
                const id = link.href.replace('#', '')
                return (
                  <button
                    key={link.href}
                    onClick={() => handleNavClick(link.href)}
                    className={cn(
                      'px-4 py-2 rounded-pill text-sm font-medium transition-all duration-200',
                      activeSection === id
                        ? 'text-brand-blue bg-brand-blue/10'
                        : 'text-white/45 hover:text-white hover:bg-white/[0.07]'
                    )}
                  >
                    {link.label}
                  </button>
                )
              })}
            </nav>

            {/* CTA */}
            <div className="hidden md:flex items-center gap-2">
              <button className="px-4 py-2 rounded-pill text-sm font-medium text-white/45 hover:text-white hover:bg-white/[0.07] transition-all duration-200">
                Giriş Yap
              </button>
              <Button variant="primary" size="sm">
                Ücretsiz Deneyin
              </Button>
            </div>

            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileOpen((v) => !v)}
              aria-label="Menüyü aç"
              className="md:hidden flex flex-col gap-1.5 p-2"
            >
              <span
                className={cn(
                  'w-5 h-0.5 bg-white/50 rounded-full transition-transform duration-200 origin-center',
                  mobileOpen && 'rotate-45 translate-y-2'
                )}
              />
              <span
                className={cn(
                  'w-5 h-0.5 bg-white/50 rounded-full transition-opacity duration-200',
                  mobileOpen && 'opacity-0'
                )}
              />
              <span
                className={cn(
                  'w-5 h-0.5 bg-white/50 rounded-full transition-transform duration-200 origin-center',
                  mobileOpen && '-rotate-45 -translate-y-2'
                )}
              />
            </button>
          </div>
        </Container>
      </motion.header>

      {/* Mobile menu */}
      <motion.div
        initial={false}
        animate={mobileOpen ? { opacity: 1, y: 0 } : { opacity: 0, y: -8 }}
        className={cn(
          'fixed top-[var(--navbar-height)] left-0 right-0 z-40 bg-ink-2/95 backdrop-blur-xl border-b border-white/[0.07] md:hidden',
          !mobileOpen && 'pointer-events-none'
        )}
      >
        <Container>
          <div className="py-4 flex flex-col gap-1">
            {NAV_LINKS.map((link) => (
              <button
                key={link.href}
                onClick={() => handleNavClick(link.href)}
                className="text-left px-4 py-3 rounded-card-sm text-sm font-medium text-white/50 hover:text-white hover:bg-white/[0.07] transition-colors"
              >
                {link.label}
              </button>
            ))}
            <div className="flex flex-col gap-2 pt-4 border-t border-white/[0.07]">
              <button className="w-full text-center px-6 py-3 rounded-pill text-sm font-medium text-white/50 hover:text-white border border-white/[0.10] hover:border-white/[0.20] transition-all duration-200">
                Giriş Yap
              </button>
              <Button variant="primary" size="md" className="w-full justify-center">
                Ücretsiz Deneyin
              </Button>
            </div>
          </div>
        </Container>
      </motion.div>
    </>
  )
}
