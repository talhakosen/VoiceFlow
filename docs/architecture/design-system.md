# VoiceFlow Design System

Marketing sitesi (`web/`) için tasarım kararları, token'lar ve kurallar.

---

## Kimlik

**"Obsidian + Electric Blue"** — Dark-first, typographic, enterprise premium.

Referanslar: Linear (extreme focus), Vercel (typographic refinement), Cursor (technical credibility via monospace).

---

## Typography

Üç katmanlı sistem — her katmanın rolü farklı.

| Katman | Font | Kullanım |
|---|---|---|
| Display | **Sora** (600–800) | Tüm h1/h2/h3 — otomatik (CSS global kuralı) |
| Body | **Inter** | Paragraf, açıklamalar, UI metni |
| Mono | **JetBrains Mono** | Sayılar, stats, kod örnekleri, section label'lar |

### CSS Global Kuralı

```css
h1, h2, h3 {
  font-family: var(--font-sora), system-ui, sans-serif;
}
```

Component bazında `font-display` class'ı eklemeye gerek yok.

### Section Label Utility

```css
.section-label {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  font-weight: 500;
}
```

Kullanım: `<span className="section-label text-brand-blue">Yetenekler</span>`

---

## Renkler

### Temel Palette

```
ink.DEFAULT  #070810   — sayfa arka planı
ink.2        #0C0E18   — elevated section (section ritmi için)
ink.3        #12151F   — card arka planı
```

### Brand

```
brand.blue         #4F7AFF   — primary accent (standard #3B82F6'dan bilinçli sapma)
brand.blue-light   #7B9FFF   — hover / text vurgusu
brand.blue-purple  #7C6BFF   — gradient bitiş rengi
```

### Gradient

```css
bg-blue-gradient: linear-gradient(135deg, #4F7AFF 0%, #7C6BFF 100%)
```

### Metin (dark üzerinde)

```
text-white          — başlıklar
text-white/80       — önemli body
text-white/50-60    — ikincil body
text-white/30-45    — muted / caption
text-white/10-15    — çok hafif ipuçları
```

### Highlight

```
accent.green  #22C55E   — verified / success badge'leri
```

---

## Section Arka Plan Ritmi

Tüm section'lar dark — zebra (açık/koyu) pattern YOK.

| Section | Arka Plan | Tailwind |
|---|---|---|
| Hero | `#070810` | `bg-brand-navy` / `bg-ink` |
| Stats | `#0C0E18` | `bg-ink-2` |
| Features | `#070810` | `bg-brand-navy` |
| HowItWorks | `#0C0E18` | `bg-ink-2` |
| Speed | `#070810` | `bg-ink` |
| Security | `#0C0E18` | `bg-ink-2` |
| Testimonials | `#070810` | `bg-ink` |
| Pricing | `#0C0E18` | `bg-brand-navy` |
| CTA | `#070810` | `bg-brand-navy` |
| Footer | `#050608` | `bg-text-primary` |

Section arası ince separator: `border-white/[0.06]`

---

## Borders & Surfaces

```
border-white/[0.06]   — section separator (çok hafif)
border-white/[0.08]   — card default border
border-white/[0.09]   — card default (biraz güçlü)
border-white/[0.12]   — button border, visible border
border-white/[0.20]   — hover / active state

bg-white/[0.04]       — card surface (dark bg üzerinde)
bg-white/[0.06]       — table header, elevated surface
```

---

## Spacing & Border Radius

```
borderRadius.card     16px    — section card
borderRadius.card-sm  12px    — küçük card, icon bg
borderRadius.pill     9999px  — button, badge
```

Section padding: `--section-gap: 120px` (mobile: 72px)

---

## Shadows

```
shadow-elevated   0 8px 32px rgba(79,122,255,0.15)
shadow-glow       0 0 40px rgba(79,122,255,0.28)
shadow-glow-sm    0 0 20px rgba(79,122,255,0.18)
```

---

## Background Patterns

### Grid Lines (tercih edilen — Linear tarzı)

```css
.grid-lines {
  background-image:
    linear-gradient(rgba(255,255,255,0.032) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.032) 1px, transparent 1px);
  background-size: 72px 72px;
}
```

### Dot Grid (eski — bazı section'larda hâlâ var)

```css
.dot-grid {
  background-image: radial-gradient(circle, rgba(79,122,255,0.10) 1px, transparent 1px);
  background-size: 32px 32px;
}
```

### Hero Gradient

```css
bg-hero-gradient: radial-gradient(ellipse 80% 50% at 50% -20%, rgba(79,122,255,0.10), transparent)
```

### Glow Orb

```css
.glow-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
}
```

Kullanım: `<div className="glow-orb w-[600px] h-[600px] bg-brand-blue/8 top-1/2 left-1/2 ..." />`

---

## Buttons

Tüm variant'lar dark-friendly.

```
primary   bg gradient from-brand-blue to-brand-blue-purple, white text
ghost     transparent, text-white/50 → text-white on hover
outline   border-brand-blue/50, text-brand-blue-light
```

Boyutlar: `sm` `md` `lg` — tümü `rounded-pill`.

---

## Navbar

- Her zaman dark — scroll'da `rgba(7,8,16,0.92)` + `blur(20px)`.
- Logo: her zaman beyaz (`brightness-0 invert`).
- Active link: `text-brand-blue bg-brand-blue/10`.
- Inactive: `text-white/45 hover:text-white hover:bg-white/[0.07]`.

---

## Animasyon

| Class | Davranış |
|---|---|
| `animate-fade-up` | Y:24px → 0, 0.6s |
| `animate-fade-in` | opacity 0 → 1, 0.4s |
| `animate-float` | yukarı-aşağı, 6s loop |
| `animate-marquee-left` | yatay scroll, `--marquee-duration` (60s) |
| `animate-blink` | cursor blink, 1s step |

Framer Motion: `FadeUp` / `StaggerContainer` / `StaggerItem` component'leri (`src/components/ui/FadeUp.tsx`).

---

## Kural: Ne Yapılmaz

- Section'lara light arka plan (`bg-white`, `bg-surface-muted`) ekleme — dark ritmi bozar.
- `#3B82F6` (stock tailwind blue) kullanma — `brand.blue` (#4F7AFF) kullan.
- `font-display` class'ını h tag'lere manuel ekleme — CSS global kuralı hallediyor.
- Glassmorphism — `glass` class'ı var ama yeni section'larda kullanma; solid surface + border tercih et.
- Glow-orb'u her section'a koyma — sadece Hero ve CTA.
