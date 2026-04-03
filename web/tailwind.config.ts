import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Design system base
        ink: {
          DEFAULT: '#070810',
          2: '#0C0E18',
          3: '#12151F',
        },
        brand: {
          navy: '#070810',
          'navy-light': '#0C0E18',
          blue: '#4F7AFF',
          'blue-light': '#7B9FFF',
          'blue-purple': '#7C6BFF',
        },
        surface: {
          DEFAULT: '#F8FAFC',
          muted: '#F1F5F9',
          dark: '#070810',
        },
        text: {
          primary: '#0F172A',
          secondary: '#64748B',
          muted: '#94A3B8',
          inverse: '#FFFFFF',
        },
        accent: {
          green: '#22C55E',
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        display: ['var(--font-sora)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        card: '16px',
        'card-sm': '12px',
        pill: '9999px',
      },
      boxShadow: {
        card: '0 4px 24px rgba(0,0,0,0.08)',
        elevated: '0 8px 32px rgba(79,122,255,0.15)',
        glow: '0 0 40px rgba(79,122,255,0.28)',
        'glow-sm': '0 0 20px rgba(79,122,255,0.18)',
      },
      animation: {
        'fade-up': 'fadeUp 0.6s ease-out forwards',
        'fade-in': 'fadeIn 0.4s ease-out forwards',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'gradient-shift': 'gradientShift 6s ease infinite',
        float: 'float 6s ease-in-out infinite',
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
        gradientShift: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-12px)' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
      },
      backgroundImage: {
        'hero-gradient':
          'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(79,122,255,0.10), transparent)',
        'card-gradient':
          'linear-gradient(135deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%)',
        'blue-gradient': 'linear-gradient(135deg, #4F7AFF 0%, #7C6BFF 100%)',
        'text-gradient':
          'linear-gradient(135deg, #7B9FFF 0%, #7C6BFF 50%, #7B9FFF 100%)',
      },
    },
  },
  plugins: [],
}

export default config
