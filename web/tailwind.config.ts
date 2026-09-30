import type { Config } from 'tailwindcss'

/**
 * VoiceFlow — Enstrüman
 *
 * Renkler CSS değişkenlerine bağlıdır (globals.css); tema geçişi
 * Tailwind'in dark: varyantı olmadan, değişken üzerinden çözülür.
 * Bu yüzden `bg-surface` her iki temada da doğru zemini verir.
 *
 * Kural: ham hex yazma. Yeni bir renk gerekiyorsa önce token olur.
 */
const config: Config = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        ground: 'rgb(var(--ground) / <alpha-value>)',
        surface: {
          DEFAULT: 'rgb(var(--surface) / <alpha-value>)',
          raised: 'rgb(var(--surface-raised) / <alpha-value>)',
          sunken: 'rgb(var(--surface-sunken) / <alpha-value>)',
        },
        control: {
          DEFAULT: 'rgb(var(--control) / <alpha-value>)',
          hover: 'rgb(var(--control-hover) / <alpha-value>)',
        },
        line: {
          DEFAULT: 'rgb(var(--line) / <alpha-value>)',
          strong: 'rgb(var(--line-strong) / <alpha-value>)',
        },
        text: {
          DEFAULT: 'rgb(var(--text) / <alpha-value>)',
          muted: 'rgb(var(--text-muted) / <alpha-value>)',
          faint: 'rgb(var(--text-faint) / <alpha-value>)',
          'on-signal': 'rgb(var(--text-on-signal) / <alpha-value>)',
        },
        signal: {
          DEFAULT: 'rgb(var(--signal) / <alpha-value>)',
          dim: 'rgb(var(--signal-dim) / <alpha-value>)',
          text: 'rgb(var(--signal-text) / <alpha-value>)',
        },
        mode: {
          general: 'rgb(var(--mode-general) / <alpha-value>)',
          engineering: 'rgb(var(--mode-engineering) / <alpha-value>)',
          office: 'rgb(var(--mode-office) / <alpha-value>)',
        },
        positive: 'rgb(var(--positive) / <alpha-value>)',
        caution: 'rgb(var(--caution) / <alpha-value>)',
        critical: 'rgb(var(--critical) / <alpha-value>)',
        wave: {
          DEFAULT: 'rgb(var(--wave) / <alpha-value>)',
          live: 'rgb(var(--wave-live) / <alpha-value>)',
        },
      },
      fontFamily: {
        display: ['var(--font-display)', 'system-ui', 'sans-serif'],
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        // Design system tip ölçeği — Web grubu
        'web-h1': ['40px', { lineHeight: '46px', letterSpacing: '-0.01em', fontWeight: '600' }],
        'web-h2': ['28px', { lineHeight: '36px', fontWeight: '600' }],
        'web-h3': ['20px', { lineHeight: '28px', fontWeight: '600' }],
        'web-body': ['16px', { lineHeight: '26px' }],
        'web-small': ['14px', { lineHeight: '22px' }],
        // Display grubu
        'display-xl': ['56px', { lineHeight: '56px', letterSpacing: '-0.02em', fontWeight: '700' }],
        'display-l': ['40px', { lineHeight: '44px', letterSpacing: '-0.02em', fontWeight: '700' }],
        'display-m': ['28px', { lineHeight: '34px', letterSpacing: '-0.01em', fontWeight: '700' }],
        // Veri grubu (mono)
        'data-l': ['20px', { lineHeight: '24px', fontWeight: '500' }],
        'data-m': ['13px', { lineHeight: '18px', fontWeight: '500' }],
        'data-s': ['11px', { lineHeight: '14px', fontWeight: '500' }],
      },
      spacing: {
        's-05': '2px',
        's-1': '4px',
        's-2': '8px',
        's-3': '12px',
        's-4': '16px',
        's-5': '20px',
        's-6': '24px',
        's-8': '32px',
        's-12': '48px',
        's-16': '64px',
      },
      borderRadius: {
        xs: '2px',
        sm: '4px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        pill: '24px',
        full: '999px',
      },
      boxShadow: {
        overlay: 'var(--shadow-overlay)',
        focus: 'var(--shadow-focus)',
      },
      animation: {
        'fade-up': 'fadeUp 0.6s ease-out forwards',
        'fade-in': 'fadeIn 0.4s ease-out forwards',
        blink: 'blink 1s step-end infinite',
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(24px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
      },
    },
  },
  plugins: [],
}

export default config
