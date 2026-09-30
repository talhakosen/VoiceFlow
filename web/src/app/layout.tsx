import type { Metadata, Viewport } from 'next'
import { Space_Grotesk, IBM_Plex_Sans, IBM_Plex_Mono } from 'next/font/google'
import { ThemeProvider } from '@/components/ThemeProvider'
import './globals.css'

// latin-ext şart: onsuz ğ ş İ ı ç ö ü fallback fonta düşer.
const display = Space_Grotesk({
  subsets: ['latin', 'latin-ext'],
  variable: '--font-display',
  display: 'swap',
  weight: ['500', '600', '700'],
})

const sans = IBM_Plex_Sans({
  subsets: ['latin', 'latin-ext'],
  variable: '--font-sans',
  display: 'swap',
  weight: ['400', '500', '600'],
})

// Her ölçüm mono yazılır: ms, sn, sürüm, PID.
const mono = IBM_Plex_Mono({
  subsets: ['latin', 'latin-ext'],
  variable: '--font-mono',
  display: 'swap',
  weight: ['400', '500'],
})

export const metadata: Metadata = {
  title: "VoiceFlow — Türkiye'nin Ses AI Platformu",
  description:
    'Sesinizi metne dönüştürün. Yapay zeka düzeltsin. Verileriniz sizde kalsın. KVKK uyumlu, on-premise kurumsal ses yazılımı.',
  keywords: [
    'ses tanıma',
    'konuşma metne çevirme',
    'KVKK uyumlu',
    'on-premise',
    'kurumsal yapay zeka',
    'Türkçe ses tanıma',
    'speech to text',
    'VoiceFlow',
  ],
  authors: [{ name: 'VoiceFlow' }],
  creator: 'VoiceFlow',
  publisher: 'VoiceFlow',
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  openGraph: {
    type: 'website',
    locale: 'tr_TR',
    url: 'https://voiceflow.com.tr',
    siteName: 'VoiceFlow',
    title: "VoiceFlow — Türkiye'nin Ses AI Platformu",
    description:
      'Sesinizi metne dönüştürün. Yapay zeka düzeltsin. Verileriniz sizde kalsın.',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'VoiceFlow — Kurumsal Ses AI',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: "VoiceFlow — Türkiye'nin Ses AI Platformu",
    description:
      'Sesinizi metne dönüştürün. Yapay zeka düzeltsin. Verileriniz sizde kalsın.',
    images: ['/og-image.png'],
  },
}

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#fbfaf7' },
    { media: '(prefers-color-scheme: dark)', color: '#0b0b0d' },
  ],
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="tr" className={`${display.variable} ${sans.variable} ${mono.variable}`}>
      <body className="antialiased">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  )
}
