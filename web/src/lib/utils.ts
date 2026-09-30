import { clsx, type ClassValue } from 'clsx'
import { extendTailwindMerge } from 'tailwind-merge'

/**
 * tailwind-merge bizim özel ölçeklerimizi tanımıyor.
 *
 * Tanımlamazsak `text-text-on-signal` gibi bir renk, font-size sanılıp çağrı
 * yerindeki `text-base` ile çakışıyor ve SESSİZCE düşüyor — buton amber zemine
 * amber yazı olarak render ediliyor (yaşandı, hero CTA'sında). Aynısı boşluk
 * ölçeği için de geçerli: `px-s-6` ile `px-10`.
 *
 * Yeni bir renk veya ölçek token'ı eklersen buraya da ekle.
 */
const COLORS = [
  'text',
  'text-muted',
  'text-faint',
  'text-on-signal',
  'ground',
  'surface',
  'surface-raised',
  'surface-sunken',
  'control',
  'control-hover',
  'line',
  'line-strong',
  'signal',
  'signal-dim',
  'signal-text',
  'mode-general',
  'mode-engineering',
  'mode-office',
  'positive',
  'caution',
  'critical',
  'wave',
  'wave-live',
]

const FONT_SIZES = [
  'display-xl',
  'display-l',
  'display-m',
  'web-h1',
  'web-h2',
  'web-h3',
  'web-body',
  'web-small',
  'data-l',
  'data-m',
  'data-s',
]

const SPACING = ['s-05', 's-1', 's-2', 's-3', 's-4', 's-5', 's-6', 's-8', 's-12', 's-16']

const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      'font-size': [{ text: FONT_SIZES }],
      'text-color': [{ text: COLORS }],
      'bg-color': [{ bg: COLORS }],
      'border-color': [{ border: COLORS }],
      'border-color-t': [{ 'border-t': COLORS }],
      'border-color-r': [{ 'border-r': COLORS }],
      'border-color-b': [{ 'border-b': COLORS }],
      'border-color-l': [{ 'border-l': COLORS }],
      'ring-color': [{ ring: COLORS }],
      'gradient-from': [{ from: COLORS }],
      'gradient-via': [{ via: COLORS }],
      'gradient-to': [{ to: COLORS }],
      p: [{ p: SPACING }],
      px: [{ px: SPACING }],
      py: [{ py: SPACING }],
      m: [{ m: SPACING }],
      mx: [{ mx: SPACING }],
      my: [{ my: SPACING }],
      gap: [{ gap: SPACING }],
    },
  },
})

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

export function formatNumber(value: number): string {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`
  }
  return value.toString()
}
