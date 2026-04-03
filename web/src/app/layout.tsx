import type { Metadata, Viewport } from 'next'
import { Inter, Sora, JetBrains_Mono } from 'next/font/google'
import './globals.css'

const sora = Sora({
  subsets: ['latin'],
  variable: '--font-sora',
  display: 'swap',
  weight: ['600', '700', '800'],
})

const inter = Inter({
  subsets: ['latin', 'latin-ext'],
  variable: '--font-inter',
  display: 'swap',
})

const mono = JetBrains_Mono({
  subsets: ['latin'],
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
  themeColor: '#070810',
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="tr" className={`${sora.variable} ${inter.variable} ${mono.variable}`}>
      <body className="antialiased">{children}</body>
    </html>
  )
}
