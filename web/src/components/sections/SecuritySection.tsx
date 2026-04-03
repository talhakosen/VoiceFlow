const CERTS = ['KVKK Uyumlu', 'BDDK Onaylı', 'ISO 27001', 'SOC 2 Type II']

const TRUST_ITEMS = [
  {
    title: 'Veriler şirketinizde kalır',
    desc: 'Yapay zeka modeli kendi sunucunuzda çalışır. Hiçbir veri dışarı çıkmaz.',
  },
  {
    title: 'Türk regülasyonlarına uygun',
    desc: 'KVKK ve BDDK gereksinimlerini karşılayacak şekilde tasarlandı. DPO desteği dahil.',
  },
  {
    title: 'Tam denetim izi',
    desc: 'Her işlem için ayrıntılı kayıt. Denetim ve uyumluluk raporlaması hazır.',
  },
]

export function SecuritySection() {
  return (
    <section id="guvenlik" className="section-padding bg-ink-2">
      <div className="max-w-5xl mx-auto px-6">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left */}
          <div>
            <span className="section-label text-brand-blue">
              Güvenlik & Uyumluluk
            </span>
            <h2 className="text-4xl lg:text-5xl font-bold text-white tracking-tight leading-tight mb-6">
              Verileriniz hiçbir zaman
              <br />
              şirketinizi terk etmez.
            </h2>
            <p className="text-lg text-white/45 mb-8 leading-relaxed">
              Türkiye&apos;nin finans ve kurumsal sektörünün güvenlik
              gereksinimlerine göre inşa edildi.
            </p>
            <div className="flex flex-wrap gap-2">
              {CERTS.map((cert) => (
                <span
                  key={cert}
                  className="inline-flex items-center gap-2 text-sm font-medium text-white/65 bg-white/[0.05] border border-white/[0.09] rounded-full px-4 py-2 hover:border-brand-blue/30 transition-colors"
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    className="w-3.5 h-3.5 text-accent-green shrink-0"
                    strokeWidth="2.5"
                    stroke="currentColor"
                  >
                    <path d="M20 6 9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  {cert}
                </span>
              ))}
            </div>
          </div>

          {/* Right */}
          <div className="flex flex-col gap-3">
            {TRUST_ITEMS.map((item) => (
              <div
                key={item.title}
                className="flex gap-4 p-5 rounded-2xl bg-ink-3 border border-white/[0.07] hover:border-brand-blue/20 transition-colors group"
              >
                <div className="w-9 h-9 rounded-xl bg-brand-blue/10 text-brand-blue-light flex items-center justify-center shrink-0 mt-0.5 group-hover:bg-brand-blue/15 transition-colors">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    className="w-4 h-4"
                    strokeWidth="1.5"
                    stroke="currentColor"
                  >
                    <path
                      d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-white mb-1.5 text-sm">{item.title}</h3>
                  <p className="text-sm text-white/45 leading-relaxed">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
