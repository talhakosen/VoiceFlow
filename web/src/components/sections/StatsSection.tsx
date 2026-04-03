const STATS = [
  { value: '98,7%', label: 'Türkçe doğruluk oranı' },
  { value: '10x', label: 'Klavyeden daha hızlı' },
  { value: '2,5 saat', label: 'Günlük kazanılan süre' },
]

export function StatsSection() {
  return (
    <section className="border-y border-white/[0.06] bg-ink-2">
      <div className="max-w-4xl mx-auto px-6">
        <div className="flex flex-col sm:flex-row divide-y sm:divide-y-0 sm:divide-x divide-white/[0.06]">
          {STATS.map((stat) => (
            <div key={stat.label} className="flex-1 text-center px-8 py-12 sm:py-10">
              <div className="text-[60px] sm:text-[72px] leading-none font-bold tracking-[-2.5px] text-white tabular-nums mb-3 font-display">
                {stat.value}
              </div>
              <div className="section-label text-white/28">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
