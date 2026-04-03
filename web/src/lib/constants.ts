import type {
  NavLink,
  Feature,
  Stat,
  TrustBadge,
  Step,
  Testimonial,
  FooterColumn,
  SocialLink,
  ComparisonRow,
  AgenticUseCase,
} from '@/types'

export const NAV_LINKS: NavLink[] = [
  { label: 'Ürün', href: '#urun' },
  { label: 'Özellikler', href: '#ozellikler' },
  { label: 'Nasıl Çalışır', href: '#nasil-calisir' },
  { label: 'Güvenlik', href: '#guvenlik' },
  { label: 'Fiyatlandırma', href: '#fiyatlandirma' },
]

export const HERO = {
  tagline: 'Yazmayı bırakın,\nkonuşun.',
  subtext: 'Konuştuğunuz her şeyi kusursuz Türkçe yazıya dönüştürür.',
  ctaPrimary: 'Ücretsiz Pilot Başlatın',
  trustedBy: 'Türkiye\'nin önde gelen kurumları güveniyor',
}

export const TYPEWRITER_EXAMPLES = [
  {
    raw: 'bugun toplantida konustugumuz butce planlamasi konusunu bir daha gozmden gecirelim',
    corrected:
      'Bugün toplantıda konuştuğumuz bütçe planlaması konusunu bir daha gözden geçirelim.',
  },
  {
    raw: 'musteri sikayet formlari icin yeni bir is akisi olusturmamiz gerekiyor',
    corrected:
      'Müşteri şikayet formları için yeni bir iş akışı oluşturmamız gerekiyor.',
  },
  {
    raw: 'kdv beyannamesini bu hafta son gun unutmayin lutfen',
    corrected:
      'KDV beyannamesini bu hafta son gün, unutmayın lütfen.',
  },
]

export const FEATURES: Feature[] = [
  {
    icon: 'Mic',
    title: 'Gerçek Zamanlı Transkripsiyon',
    description:
      'Konuşurken metne dönüştürün. 150ms\'nin altında gecikmeyle kurumsal doğrulukta transkripsiyon.',
    highlight: true,
  },
  {
    icon: 'Brain',
    title: 'Yapay Zeka Düzeltme',
    description:
      'Noktalama, büyük harf ve Türkçe karakter hatalarını yerel yapay zeka modeliyle otomatik düzeltin.',
  },
  {
    icon: 'Lock',
    title: 'On-Premise Kurulum',
    description:
      'Verileriniz hiçbir zaman sunucularınızı terk etmez. Tam KVKK ve BDDK uyumluluğu.',
  },
  {
    icon: 'Building2',
    title: 'Kurumsal Entegrasyon',
    description:
      'REST API ile mevcut sistemlerinize kolayca entegre edin. SAP, Teams, Outlook desteği.',
    highlight: true,
  },
  {
    icon: 'Globe',
    title: 'Türkçe\'ye Özel Eğitilmiş',
    description:
      'Türkçe\'ye özel eğitilmiş model. Teknik jargon, finans ve hukuk terminolojisi desteği.',
  },
  {
    icon: 'Zap',
    title: 'Mac İçin Yerli Güç',
    description:
      'Apple M-serisi işlemciler için özel olarak tasarlandı. Bulut bağlantısı olmadan, cihazınızın tüm gücünden yararlanır.',
  },
]

export const STATS: Stat[] = [
  {
    value: '98.7',
    suffix: '%',
    label: 'Doğruluk Oranı',
    description: 'Türkçe konuşma tanımada',
  },
  {
    value: '10',
    suffix: 'x',
    label: 'Daha Hızlı Yazım',
    description: 'Klavyeyle yazmaya kıyasla',
  },
  {
    value: '150',
    suffix: 'ms',
    label: 'Gecikme',
    description: 'Gerçek zamanlı transkripsiyon',
  },
  {
    value: '500',
    suffix: '+',
    label: 'Kurumsal Kullanıcı',
    description: 'Türkiye genelinde aktif',
  },
]

export const TRUST_BADGES: TrustBadge[] = [
  {
    label: 'KVKK Uyumlu',
    icon: 'Shield',
    description: 'Kişisel Verilerin Korunması Kanunu\'na tam uyumluluk',
  },
  {
    label: 'On-Premise',
    icon: 'Server',
    description: 'Veriler kendi sunucunuzda kalır',
  },
  {
    label: 'ISO 27001',
    icon: 'Award',
    description: 'Bilgi güvenliği yönetim sistemi sertifikası',
  },
  {
    label: 'Uçtan Uca Şifreleme',
    icon: 'Lock',
    description: 'AES-256 şifreleme ile tam veri güvenliği',
  },
]

export const HOW_IT_WORKS: Step[] = [
  {
    step: '01',
    title: 'Kurulum',
    description:
      'VoiceFlow\'u kendi altyapınıza kurun. Buluta bağlanmadan, 15 dakikada çalışmaya hazır.',
    icon: 'Download',
  },
  {
    step: '02',
    title: 'Konuşun',
    description:
      'Bir tuşa basın ve konuşmaya başlayın. Yapay zeka metni anında düzeltir, imlecin bulunduğu alana yapıştırır.',
    icon: 'Mic',
  },
  {
    step: '03',
    title: 'Veriminizi Artırın',
    description:
      'Günde ortalama 2,5 saat kazanın. Tüm bunlar verileriniz kurumunuzun sınırları dışına çıkmadan gerçekleşir.',
    icon: 'TrendingUp',
  },
]

export const TESTIMONIALS: Testimonial[] = [
  {
    quote:
      'VoiceFlow\'u kullanmaya başladıktan sonra raporlama süremiz yarıya indi. Türkçe yazım kalitesi inanılmaz — özellikle teknik terminoloji çok iyi.',
    author: 'Ahmet Yıldırım',
    title: 'CTO',
    company: 'Teknosa',
    avatar: 'AY',
  },
  {
    quote:
      'KVKK uyumluluğu bizim için kritikti. On-premise kurulum sayesinde verilerimizin güvenliğinden emin olduk. Hukuk departmanımız çok memnun.',
    author: 'Selin Kaya',
    title: 'Hukuk Direktörü',
    company: 'Garanti BBVA',
    avatar: 'SK',
  },
  {
    quote:
      'Müşteri görüşmelerini otomatik olarak metne dönüştürüyor, CRM\'e aktarıyoruz. Entegrasyon 2 günde tamamlandı. Destek ekibi müthiş yardımcı oldu.',
    author: 'Murat Demir',
    title: 'Dijital Dönüşüm Müdürü',
    company: 'Turkcell',
    avatar: 'MD',
  },
]

export const COMPARISON_ROWS: ComparisonRow[] = [
  { feature: 'İçerik üretim hızı', keyboard: '40 kelime/dk', voice: '400 kelime/dk' },
  { feature: 'Türkçe karakter hatası', keyboard: 'Sık görülür', voice: 'Otomatik düzeltilir' },
  { feature: 'Odak kaybı', keyboard: 'Yüksek', voice: 'Minimal' },
  { feature: 'Veri güvenliği', keyboard: 'Bulut\'a bağımlı', voice: 'On-Premise' },
]

export const FOOTER_COLUMNS: FooterColumn[] = [
  {
    title: 'Ürün',
    links: [
      { label: 'Özellikler', href: '#ozellikler' },
      { label: 'Güvenlik', href: '#guvenlik' },
      { label: 'Fiyatlandırma', href: '#fiyatlandirma' },
      { label: 'API Dokümantasyonu', href: '#' },
      { label: 'Sürüm Notları', href: '#' },
    ],
  },
  {
    title: 'Kurumsal',
    links: [
      { label: 'Kurumsal Çözümler', href: '#kurumsal' },
      { label: 'On-Premise Kurulum', href: '#' },
      { label: 'KVKK Uyumluluğu', href: '#' },
      { label: 'SLA Garantisi', href: '#' },
      { label: 'Destek', href: '#' },
    ],
  },
  {
    title: 'Şirket',
    links: [
      { label: 'Hakkımızda', href: '#' },
      { label: 'Blog', href: '#' },
      { label: 'Kariyer', href: '#' },
      { label: 'İletişim', href: '#' },
      { label: 'Basın Kiti', href: '#' },
    ],
  },
  {
    title: 'Hukuki',
    links: [
      { label: 'Gizlilik Politikası', href: '#' },
      { label: 'Kullanım Koşulları', href: '#' },
      { label: 'KVKK Aydınlatma', href: '#' },
      { label: 'Çerez Politikası', href: '#' },
    ],
  },
]

export const SOCIAL_LINKS: SocialLink[] = [
  { label: 'Twitter', href: 'https://twitter.com', icon: 'Twitter' },
  { label: 'LinkedIn', href: 'https://linkedin.com', icon: 'Linkedin' },
  { label: 'GitHub', href: 'https://github.com', icon: 'Github' },
]

export const TRUSTED_LOGOS = [
  'Garanti BBVA',
  'Turkcell',
  'İş Bankası',
  'Borusan',
  'Sabancı',
  'Koç Holding',
]

export const CTA_SECTION = {
  title: 'Kurumunuzu geleceğe taşıyın.',
  subtitle:
    'Türkiye\'nin önde gelen kurumlarının tercih ettiği yapay zeka destekli ses yazılımını bugün deneyin.',
  ctaPrimary: 'Ücretsiz Pilot Başlatın',
  ctaSecondary: 'Uzmanla Konuşun',
  disclaimer: '14 günlük ücretsiz pilot. Kredi kartı gerekmez. Verileriniz sizde kalır.',
}

export const SECURITY_SECTION = {
  title: 'Güvenlik, Her Şeyin Temeli',
  subtitle:
    'Kurumsal verileriniz için en yüksek güvenlik standartlarını en baştan tasarladık.',
  features: [
    {
      icon: 'Server',
      title: 'On-Premise Kurulum',
      description:
        'Yapay zeka modelleri kendi sunucunuzda çalışır. Hiçbir veri dışarı çıkmaz.',
    },
    {
      icon: 'Shield',
      title: 'KVKK & BDDK Uyumlu',
      description:
        'Türk regülasyonlarına tam uyumluluk. DPO desteği ve uyumluluk raporu dahil.',
    },
    {
      icon: 'Key',
      title: 'Sıfır Güven Mimarisi',
      description:
        'Gelişmiş kimlik doğrulama, kullanıcı izolasyonu ve rol tabanlı erişim kontrolü ile kurumunuzun verisi yalnızca yetkililere açık.',
    },
    {
      icon: 'FileCheck',
      title: 'Tam Denetim İzi',
      description:
        'Her transkripsiyon için detaylı log. Denetim, uyumluluk ve adli analiz desteği.',
    },
  ],
}

export const DEMO_STRIP = {
  examples: [
    {
      context: 'E-posta',
      raw: 'merhaba toplantı notlarını paylaşabilir misiniz geçen haftaki bütçe görüşmesinden',
      corrected: 'Merhaba, geçen haftaki bütçe görüşmesine ait toplantı notlarını paylaşabilir misiniz?',
    },
    {
      context: 'Claude Code\'a prompt',
      raw: 'authentication servisinde token refresh metodunu güncelle access 15 dk refresh 7 gün redis cache ekle',
      corrected: 'Authentication servisinde token refresh metodunu güncelle. Access token 15 dakika, refresh token 7 gün. Redis cache ekle.',
    },
    {
      context: 'Raporlama',
      raw: 'bu çeyrekte satış hedefinin yüzde seksenine ulaştık ana engel tedarik zinciri gecikmeleri oldu',
      corrected: 'Bu çeyrekte satış hedefinin %80\'ine ulaştık. Ana engel tedarik zinciri gecikmeleri oldu.',
    },
    {
      context: 'Commit mesajı',
      raw: 'stripe webhook handler eklendi idempotency key kontrolü var retry logic 3 deneme yapıyor',
      corrected: 'feat(payment): Stripe webhook handler eklendi — idempotency key kontrolü ve 3 deneme retry logic\'i.',
    },
  ],
}

export const AGENTIC_SECTION = {
  badge: 'Yazılım Ekipleri İçin',
  title: 'Ajansal geliştirmenin\nhızına yetişin.',
  subtitle:
    'Claude, Cursor veya Copilot kullanıyorsanız, en büyük darboğaz artık kod yazmak değil — doğru promptu yazmak. VoiceFlow, düşüncelerinizi klavyeden 10 kat hızlı yapay zekanıza iletir.',
  useCases: [
    {
      icon: 'MessageSquare',
      title: 'Prompt\'ı Konuşarak Yaz',
      description:
        'Claude Code\'a, Cursor\'a ya da Copilot Chat\'e vermek istediğin talimatı kafanda kurduğun an konuş. VoiceFlow metne döker, siz gözden geçirip gönderin.',
      example: {
        raw: 'authentication servisinde token refresh metodunu yenile, access token 15 dk, refresh token 7 gün olsun, redis cache ekle',
        label: 'Claude Code\'a gönderildi',
      },
      highlight: true,
    },
    {
      icon: 'GitCommit',
      title: 'Commit & PR Açıklaması',
      description:
        'Yaptığın değişikliği sesle anlat — commit mesajı ve PR açıklaması hazır. Kod tabanınızdaki sınıf ve fonksiyon isimlerini zaten tanır.',
      example: {
        raw: 'payment gateway\'de stripe webhook handler eklendi, idempotency key kontrolü, retry logic 3 deneme',
        label: 'Git commit mesajına dönüştürüldü',
      },
    },
    {
      icon: 'FileText',
      title: 'Teknik Doküman & Yorum',
      description:
        'Fonksiyonun ne yaptığını sesle açıkla, kod yorumu veya README bölümü olarak yapıştır. Teknik terimleri bozmaz.',
      example: {
        raw: 'bu metod kullanıcının JWT tokenını decode edip claim\'leri döner, geçersiz token\'da unauthorized fırlatır',
        label: 'Kod yorumuna eklendi',
      },
    },
    {
      icon: 'Bug',
      title: 'Bug Raporu & Ticket',
      description:
        'Hatayı keşfettiğin an sesle anlat — Jira veya Linear ticket\'ı için yapılandırılmış metin anında hazır.',
      example: {
        raw: 'production\'da checkout akışında order service timeout veriyor, cart service\'den dönen response 5 saniyeden fazla sürüyor',
        label: 'Jira ticket\'ına yapıştırıldı',
      },
    },
  ] as AgenticUseCase[],
  stats: [
    { value: '4x', label: 'Daha hızlı prompt yazımı' },
    { value: '%0', label: 'Bulut verisi — sıfır' },
    { value: '169+', label: 'IT terimi tanıma' },
  ],
}
