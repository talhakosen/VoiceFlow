"""Seed training sentences into the VoiceFlow SQLite database.

Run once:
    python -m voiceflow.db.seed_sentences

Idempotent: inserts only if sentences table is empty (count == 0).
Covers patterns Whisper struggles with:
- Long compound sentences
- Technical terms / proper nouns (foreign names)
- Numbers, dates, percentages
- Turkish place names and person names
- Mixed language phrases
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentence corpus — 70+ per domain, 3 domains
# ---------------------------------------------------------------------------

SENTENCES: list[tuple[str, str, str]] = [
    # (domain, difficulty, text)

    # -----------------------------------------------------------------------
    # GENERAL — everyday Turkish, news-style, public figures, place names
    # -----------------------------------------------------------------------
    ("general", "easy",   "Bugün hava çok güzel, piknik yapmak için ideal bir gün."),
    ("general", "easy",   "Marketten ekmek, süt ve yoğurt aldım."),
    ("general", "easy",   "Toplantı saat üçte başlayacak, lütfen geç kalmayın."),
    ("general", "easy",   "Akşam yemeğinde mercimek çorbası ve ızgara köfte yedik."),
    ("general", "easy",   "Kitabı yarın iade etmem gerekiyor yoksa ceza öderim."),
    ("general", "medium", "Türkiye Büyük Millet Meclisi, 1920 yılında Ankara'da kuruldu."),
    ("general", "medium", "İstanbul'un nüfusu on beş milyonu aşmış durumda."),
    ("general", "medium", "Cumhurbaşkanı Recep Tayyip Erdoğan, konuşmasında ekonomi reformlarına değindi."),
    ("general", "medium", "Galatasaray dün akşam Beşiktaş'ı iki sıfır mağlup etti."),
    ("general", "medium", "Fenerbahçe Spor Kulübü, yeni transferleri için yüz milyon euro harcadı."),
    ("general", "medium", "Antalya'da bu yaz turizm geliri geçen yıla göre yüzde otuz arttı."),
    ("general", "medium", "Ankara Esenboğa Havalimanı'ndan Londra Heathrow'a direkt sefer başladı."),
    ("general", "medium", "Yüksek Seçim Kurulu, sonuçları saat yirmi birde açıklayacak."),
    ("general", "medium", "Karadeniz kıyısındaki Trabzon, fındık üretiminde dünya birincisi."),
    ("general", "hard",   "Türkiye Cumhuriyet Merkez Bankası, politika faizini yüzde elli beşten yüzde elliye indirdi."),
    ("general", "hard",   "Süper Lig'de bu sezon toplam dört yüz seksen sekiz gol atıldı."),
    ("general", "hard",   "UNESCO Dünya Mirası listesindeki Efes Antik Kenti'ni geçen yıl üç milyon turist ziyaret etti."),
    ("general", "hard",   "Dışişleri Bakanı Hakan Fidan, New York'taki Birleşmiş Milletler Genel Kurulu'nda konuştu."),
    ("general", "hard",   "İzmir Büyükşehir Belediyesi, toplu taşımada elli bin yolcu kapasiteli yeni araçlar aldı."),
    ("general", "hard",   "Meteoroloji Genel Müdürlüğü, Ege ve Akdeniz kıyılarında kuvvetli lodos uyarısı verdi."),
    ("general", "hard",   "Zeynep Arslan, yirmi üç yaşında Türkiye'nin en genç olimpik altın madalyacısı oldu."),
    ("general", "hard",   "Orhan Pamuk'un son romanı otuz dört dile çevrildi ve dünya genelinde iki milyon satış yaptı."),
    ("general", "hard",   "Koç Holding'in yıllık cirosu üç yüz milyar Türk lirasını aştı."),
    ("general", "medium", "Boğaziçi Köprüsü her gün ortalama iki yüz elli bin araç trafiğine hizmet veriyor."),
    ("general", "medium", "Kapadokya'daki balon turları şafakta kalkış yapıyor ve bir saat sürüyor."),
    ("general", "medium", "Türk Hava Yolları, bu yıl yüz yirmi ülkeye sefer düzenliyor."),
    ("general", "easy",   "Pazar sabahı komşularımla çay içtim ve sohbet ettik."),
    ("general", "easy",   "Çocuklar bahçede top oynuyor, çok eğleniyorlar."),
    ("general", "medium", "Kanal İstanbul projesi hâlâ tartışmalıdır ve ekonomik maliyeti belirsizdir."),
    ("general", "medium", "Marmara Üniversitesi'nden mezun olmak için dört yüz seksen kredi gerekiyor."),
    ("general", "hard",   "TRT Haber'in yayın akışında sabah altıdan gece yarısına kadar canlı yayın yapılıyor."),
    ("general", "medium", "Ahmet Kaya'nın türküleri bugün hâlâ milyonlar tarafından dinleniyor."),
    ("general", "hard",   "Gaziantep'in baklavası coğrafi işaret tescili ile Avrupa'da koruma altına alındı."),
    ("general", "easy",   "Yarın sabah erken kalkıp yürüyüşe çıkmayı planlıyorum."),
    ("general", "medium", "Şanlıurfa, Göbekli Tepe kazıları sayesinde dünya arkeoloji gündemine girdi."),
    ("general", "hard",   "Türkiye İstatistik Kurumu verilerine göre enflasyon Mayıs ayında yüzde elli yediye geriledi."),
    ("general", "medium", "Mustafa Kemal Atatürk, on dört Mayıs bin sekiz yüz seksen birinde Selanik'te doğdu."),
    ("general", "hard",   "Bursaspor, elli bin kişilik Timsah Arena stadyumunu bin dokuz yüz seksen yılında kurdu."),
    ("general", "medium", "Nevşehir'deki yeraltı şehri Derinkuyu, sekiz katlı ve yirmi bin kişiyi barındırabilecek kapasitede."),
    ("general", "easy",   "Sağlıklı bir yaşam için günde en az iki litre su içmeliyiz."),
    ("general", "medium", "Rize çayı dünyanın en kaliteli çayları arasında gösterilmektedir."),
    ("general", "hard",   "Türkiye 2053 vizyon belgesi, sıfır karbon ve dijital dönüşümü öncelikli hedef olarak belirliyor."),
    ("general", "medium", "Konya Mevlana Müzesi her yıl on milyon ziyaretçiye ev sahipliği yapıyor."),
    ("general", "hard",   "İstanbul Finans Merkezi, 2024 yılında faaliyete geçerek Avrupa'nın en büyük finans kümelenmelerinden biri oldu."),
    ("general", "easy",   "Akşam haberleri saat sekizde başlıyor, kaçırmayalım."),
    ("general", "medium", "Türkiye geçen yıl kırk beş milyon turist ağırladı ve elli iki milyar dolar turizm geliri elde etti."),
    ("general", "hard",   "ÇOMÜ Fen Edebiyat Fakültesi'nden Dr. Elif Şahin, kuantum fiziği alanında uluslararası bir ödül aldı."),
    ("general", "medium", "Adana kebabı, iki yüz gram kıyma ve özel baharatlarla hazırlanıyor."),
    ("general", "easy",   "Sabah kahvaltısında peynir, zeytin ve domates yemek sağlıklıdır."),
    ("general", "medium", "İzmir Enternasyonal Fuarı bu yıl yüz yirminci yılını kutluyor."),
    ("general", "hard",   "Türk Devlet Tiyatroları sezonu Ankara, İstanbul ve İzmir'de eş zamanlı açtı."),
    ("general", "medium", "Şile, İstanbul'un en güzel plajlarından birine sahip bir ilçedir."),
    ("general", "medium", "Kartal köprüsünün inşaatı üç yılda tamamlanacak ve iki milyar euro'ya mal olacak."),
    ("general", "easy",   "Kütüphanede sakin çalışmak verimliliği artırıyor."),
    ("general", "hard",   "Selçuk Bayraktar'ın geliştirdiği Bayraktar TB2, savunma sanayiinde ihracat rekoru kırdı."),
    ("general", "medium", "Bolu Dağı Tüneli, yirmi yedi yıl süren çalışmaların ardından açıldı."),
    ("general", "medium", "Çanakkale Köprüsü, iki bin yüz seksen iki metre açıklığıyla dünyanın en uzun köprüsüdür."),
    ("general", "hard",   "Hürriyet gazetesi geçen ay dijital abonelerini yüzde kırk artırarak beş yüz bine ulaştı."),
    ("general", "easy",   "Her hafta sonu ailecek pikniğe gidiyoruz."),
    ("general", "medium", "Van Gölü'nün yüzölçümü üç bin yedi yüz elli sekiz kilometrekaredir."),
    ("general", "hard",   "Türkiye Varlık Fonu, Türk Telekom hisselerinin yüzde elli beşini satın aldı."),
    ("general", "medium", "Noel Baba efsanesi, Demre'deki Aziz Nikolaos'a dayanmaktadır."),
    ("general", "hard",   "Cumhuriyet Bayramı kutlamaları kapsamında Atatürk Kültür Merkezi'nde bin sanatçı sahne aldı."),
    ("general", "easy",   "Yemekten sonra tatlı olarak baklava yedik."),
    ("general", "medium", "Pamukkale travertenleri, doğal mineral kaplıcaları ile her yıl milyonlarca ziyaretçi çekiyor."),
    ("general", "medium", "Topkapı Sarayı'ndaki Hırka-i Saadet Dairesi her yıl Ramazan ayında ziyaretçilere açılıyor."),
    ("general", "hard",   "Sabancı Üniversitesi'nden Profesör Dr. Ayşe Yılmaz, Avrupa Araştırma Konseyi'nden beş milyon euroluk hibe aldı."),
    ("general", "medium", "Türkiye'nin en yüksek dağı Ağrı, beş bin yüz yirmi yedi metre yüksekliğe sahiptir."),
    ("general", "easy",   "Bugün spor salonunda bir saat antrenman yaptım."),
    ("general", "hard",   "Türkiye'nin yenilenebilir enerji kapasitesi yüz yirmi iki bin megawat sınırını geçti."),

    # -----------------------------------------------------------------------
    # ENGINEERING — technical terms, code, system concepts, numbers
    # -----------------------------------------------------------------------
    ("engineering", "easy",   "Uygulamanın yeni sürümünü bugün production'a deploy ettim."),
    ("engineering", "easy",   "Veritabanı bağlantısı zaman aşımına uğradı, yeniden bağlanıyorum."),
    ("engineering", "easy",   "Git commit'i atmadan önce branch'i review etmek gerekiyor."),
    ("engineering", "medium", "Kubernetes cluster'ında pod'lar CrashLoopBackOff durumuna geçti, log'lara bakıyorum."),
    ("engineering", "medium", "PostgreSQL sorgusu için EXPLAIN ANALYZE komutu çalıştırıyorum."),
    ("engineering", "medium", "API gateway'de rate limiting'i redis ile implement ettik, saniyede bin istek sınırı var."),
    ("engineering", "medium", "Docker Compose dosyasında NGINX reverse proxy'yi upstream servislere bağladık."),
    ("engineering", "medium", "React uygulaması için webpack bundle size'ı iki yüz kilobaytın altına indirdik."),
    ("engineering", "medium", "MLX framework kullanarak Apple Silicon üzerinde Whisper modelini fine-tune ediyoruz."),
    ("engineering", "hard",   "Transformer mimarisinde self-attention mekanizması O(n²) karmaşıklığa sahip."),
    ("engineering", "hard",   "BERT, GPT ve T5 gibi büyük dil modelleri tokenizasyon için Byte-Pair Encoding kullanıyor."),
    ("engineering", "hard",   "Llama 3.1 seksen milyar parametreli modeli dört bit kuantizasyon ile kırk gigabayta indiriyoruz."),
    ("engineering", "hard",   "gRPC servisinde protobuf schema'yı güncelleyip backward compatibility'yi korumak gerekiyor."),
    ("engineering", "hard",   "Elasticsearch'te inverted index yapısı, full-text arama için O(1) lookup sağlıyor."),
    ("engineering", "medium", "CI/CD pipeline'ı GitHub Actions ile kurdum, merge sonrası otomatik test çalışıyor."),
    ("engineering", "medium", "Terraform ile AWS üzerinde VPC, subnet ve security group tanımlarını yaptık."),
    ("engineering", "easy",   "Python'da async-await kullanarak I/O bound işlemleri paralel yürütüyoruz."),
    ("engineering", "medium", "TypeScript'te generic type parametresi kullanarak reusable bir hook yazdık."),
    ("engineering", "hard",   "Kafka consumer group'unda partition rebalancing sırasında offset commit kaybolmamalı."),
    ("engineering", "hard",   "ChromaDB'de cosine similarity ile embedding vektörlerini top-k retrieve yapıyoruz."),
    ("engineering", "medium", "FastAPI endpoint'ine Pydantic model ekleyerek request validation yaptık."),
    ("engineering", "medium", "SwiftUI'de @Observable macro ile MVVM pattern'ı implement ettik."),
    ("engineering", "easy",   "Xcode'da DerivedData'yı temizlemeden build hatası alıyorum."),
    ("engineering", "hard",   "Metal API kullanarak GPU shader'larını M3 Pro çipinde benchmark ettik."),
    ("engineering", "hard",   "OpenTelemetry ile distributed tracing kurarak Jaeger'de trace'leri gözlemledik."),
    ("engineering", "medium", "Redis Pub/Sub ile microservice'ler arası event-driven iletişim sağladık."),
    ("engineering", "medium", "Next.js app router'da server component ve client component ayrımını doğru yapmak gerekiyor."),
    ("engineering", "hard",   "Raft consensus algoritması, leader election'da majority quorum gerektirir."),
    ("engineering", "hard",   "SQLite WAL mode'da concurrent reader'lar writer'ı bloke etmiyor."),
    ("engineering", "medium", "Prometheus metriklerini Grafana dashboard'una bağladık, p99 latency grafiği izliyoruz."),
    ("engineering", "easy",   "SSL sertifikası süresi dolmuş, Let's Encrypt ile yeniliyorum."),
    ("engineering", "medium", "WebSocket bağlantısını CloudFlare'in proxy'si kapatıyor, TCP ping ekliyorum."),
    ("engineering", "hard",   "Qwen2.5 yedi milyar parametreli modeli MLX ile MacBook Pro'da saniyede otuz token üretiyor."),
    ("engineering", "medium", "aiosqlite ile asenkron veritabanı işlemleri yaparak FastAPI event loop'unu bloke etmiyoruz."),
    ("engineering", "hard",   "Apple Neural Engine, Core ML modellerini CPU'ya göre on kat daha hızlı çalıştırıyor."),
    ("engineering", "medium", "Hugging Face'den model indirirken HF_TOKEN environment variable'ı gerekiyor."),
    ("engineering", "hard",   "Mixtral sekiz kere yedi milyar modeli sparse mixture-of-experts mimarisi kullanıyor."),
    ("engineering", "medium", "RunPod serverless endpoint'inde cold start süresi yaklaşık on iki saniye."),
    ("engineering", "easy",   "pip install -e .[dev] komutu ile editable modda kurulum yapıyorum."),
    ("engineering", "medium", "JWT token'ının access token süresi on beş dakika, refresh token süresi otuz gün."),
    ("engineering", "hard",   "LLM inference sırasında KV cache mekanizması context window'u belleğe alıyor."),
    ("engineering", "medium", "Ollama'yı RunPod üzerinde OLLAMA_HOST=0.0.0.0 ile başlatmak gerekiyor."),
    ("engineering", "hard",   "whisper-small modeli beam search ile beş alternatif transkripsiyon üretiyor."),
    ("engineering", "medium", "FastAPI'de Depends injection ile test sırasında mock servis enjekte ediyoruz."),
    ("engineering", "hard",   "macOS Accessibility API'sinde AXUIElementCopyAttributeValue ile focused window title okunuyor."),
    ("engineering", "medium", "Core Data yerine aiosqlite tercih ettik çünkü cross-platform destek gerekiyor."),
    ("engineering", "easy",   "Python 3.14'ün yeni özellikleri arasında free-threaded GIL var."),
    ("engineering", "hard",   "Vectorized embedding işlemi sentence-transformers ile CPU'da saniyede iki yüz cümle."),
    ("engineering", "medium", "Docker multi-stage build ile final image'ı seksen megabayta indirdik."),
    ("engineering", "hard",   "Whisper encoder, log-Mel spectrogram'ı seksen kanal ile işleyerek encoder states üretiyor."),
    ("engineering", "medium", "GitHub Copilot suggestion'larını her zaman review etmek gerekiyor."),
    ("engineering", "easy",   "ruff check ile kod stil hatalarını otomatik düzeltiyorum."),
    ("engineering", "hard",   "NSPanel floating window için collectionBehavior'ı canJoinAllSpaces olarak ayarlamak gerekiyor."),
    ("engineering", "medium", "NGINX'te upstream keepalive ile backend bağlantı havuzu tutuyoruz."),
    ("engineering", "medium", "Alembic migration script'i otomatik generate ettim ancak review gerekiyor."),
    ("engineering", "hard",   "Apple Silicon M3 çipinde MLX ThreadPoolExecutor max_workers=1 olmalı çünkü Metal thread-safe değil."),
    ("engineering", "medium", "ChromaDB tenant izolasyonu için her şirkete ayrı collection açıyoruz."),
    ("engineering", "easy",   "uvicorn --reload flag'i ile geliştirme sunucusunu başlatıyorum."),
    ("engineering", "hard",   "faster-whisper kütüphanesi numpy array yerine BytesIO ile soundfile WAV formatı alıyor."),
    ("engineering", "medium", "Sentry entegrasyonu ile production hataları otomatik raporlanıyor."),
    ("engineering", "hard",   "ARM64 mimarisinde NEON SIMD intrinsics ile matris çarpımı dört kat hızlandı."),
    ("engineering", "medium", "Pydantic v2'de model_config ile JSON alias üretimi yapılandırılıyor."),
    ("engineering", "easy",   "Virtual environment'ı yanlışlıkla sildim, yeniden oluşturmam gerekiyor."),
    ("engineering", "hard",   "LangChain'de ReAct agent, tool call ve observation döngüsünü yönetiyor."),
    ("engineering", "medium", "CloudFlare Workers'da V8 isolate başlangıç süresi beş mili saniyenin altında."),
    ("engineering", "medium", "GitHub Actions matrix build'de beş farklı Python versiyonunu test ediyoruz."),
    ("engineering", "hard",   "LoRA fine-tuning ile yedi milyar parametreli modeli dört GPU saatinde adapt ettik."),
    ("engineering", "medium", "Airflow DAG'ı her sabah saat 06:00 UTC'de çalışacak şekilde schedule ettik."),
    ("engineering", "easy",   "README'ye kurulum adımlarını ekledim."),
    ("engineering", "hard",   "Istio service mesh'te mTLS ile servisler arası şifreleme zorunlu hale getirildi."),
    ("engineering", "medium", "SwiftData yerine NSPanel pattern tercih ettik çünkü Settings scene debug'da güvenilmez."),
    ("engineering", "hard",   "BPE tokenizer'da vocabulary size'ı elli iki binden artırmak Türkçe kalitesini artırıyor."),
    ("engineering", "medium", "Xcode'da accessibility iznini her binary değişiminden sonra yeniden vermek gerekiyor."),

    # -----------------------------------------------------------------------
    # OFFICE — meetings, business, finance, HR, corporate language
    # -----------------------------------------------------------------------
    ("office", "easy",   "Toplantı notlarını onedrive'a yükledim, herkesle paylaşın."),
    ("office", "easy",   "Bütçe raporu Cuma'ya kadar teslim edilmeli."),
    ("office", "easy",   "İK departmanıyla koordineli olarak onboarding takvimini hazırladık."),
    ("office", "medium", "Q3 hedeflerimize göre satış geliri beklentisi yüzde on beş artış yönünde güncellendi."),
    ("office", "medium", "Yönetim Kurulu toplantısında stratejik ortaklık teklifini sunum yaparak anlattım."),
    ("office", "medium", "KPI'larımızı OKR metodolojisine göre yeniden yapılandırmamız gerekiyor."),
    ("office", "medium", "Pazarlama bütçesinin yüzde otuzunu dijital kanallara, yüzde yetmişini geleneksel medyaya ayırdık."),
    ("office", "medium", "Çeyrek sonu kapanış toplantısında EBITDA'yı yüz elli milyon lira olarak raporladık."),
    ("office", "hard",   "Yatırımcı sunumunda NPV hesabını yüzde on iki iskonto oranı üzerinden yaptık."),
    ("office", "hard",   "IFRS 16 standardına göre kiralama sözleşmeleri bilanço aktifine alınmak zorunda."),
    ("office", "hard",   "ESG raporumuzda Scope 1 ve Scope 2 karbon emisyonlarını bağımsız denetçiye doğrulattık."),
    ("office", "medium", "SLA kapsamında sistemin yüzde doksan dokuz virgül dokuz uptime sağlaması gerekiyor."),
    ("office", "medium", "Müşteri memnuniyeti anketinde NPS skorumuz seksen üçe yükseldi."),
    ("office", "hard",   "Due diligence süreci tamamlandığında share purchase agreement imzalanacak."),
    ("office", "medium", "Sprint retrospektifinde velocity'nin düştüğünü tespit ettik, ekiple aksiyon aldık."),
    ("office", "easy",   "Haftalık durum raporunu Pazartesi sabahı göndereceğim."),
    ("office", "hard",   "Tedarik zinciri aksaklıkları nedeniyle COGS yüzde on iki arttı, gross margin baskı altında."),
    ("office", "medium", "İş sürekliliği planı kapsamında DR ortamını her altı ayda bir test ediyoruz."),
    ("office", "medium", "Yeni CRM sistemine geçiş için Salesforce ile üç yıllık enterprise lisans anlaşması imzalandı."),
    ("office", "hard",   "Marka değerlememizde DCF yöntemiyle beş yıllık projeksiyon hazırladık."),
    ("office", "medium", "Çalışan bağlılığı anketinde eNPS puanı geçen yıla göre on beş puan iyileşti."),
    ("office", "hard",   "Borç/Özkaynak oranımız 0.45'ten 0.38'e geriledi, bu finansal sağlık açısından olumlu."),
    ("office", "medium", "Product roadmap için MoSCoW önceliklendirmesi yapıp paydaşlara sunduk."),
    ("office", "easy",   "Avukatımız sözleşmeyi inceleyip iki gün içinde geri dönecek."),
    ("office", "hard",   "Konsolidasyon sürecinde goodwill amortismanı ve impairment testi UFRS 3'e göre yapıldı."),
    ("office", "medium", "Dijital dönüşüm projesi Gartner Hype Cycle'ın olgunluk aşamasına ulaştı."),
    ("office", "hard",   "Transfer pricing politikamızı OECD BEPS 13. aksiyon planına uygun olarak güncelledik."),
    ("office", "medium", "Customer success ekibi churn rate'i yüzde beşten yüzde ikiye indirdi."),
    ("office", "medium", "ERP sisteminin upgrade'i sırasında iki günlük downtime planlandı."),
    ("office", "hard",   "Amortisman muhasebesi için azalan bakiyeler yöntemi yerine doğrusal yönteme geçtik."),
    ("office", "easy",   "Çalışanlara yıllık izin haklarını hatırlatmak için email gönderdik."),
    ("office", "medium", "Rekabet kurumu incelemesi için gerekli belgeleri hukuk departmanıyla hazırladık."),
    ("office", "hard",   "Sektör kıyaslamamızda benchmarking için McKinsey küresel verimlilik endeksini kullandık."),
    ("office", "medium", "PMO ofisi, proje portföyünü Jira'dan Power BI'a aktararak yöneticilere raporluyor."),
    ("office", "medium", "Tedarikçi değerlendirme matrisi, kalite, maliyet ve teslimat puanlarından oluşuyor."),
    ("office", "hard",   "Nakit akış tablosunu dolaylı yöntemle hazırlayarak net işletme sermayesi değişimini gösterdik."),
    ("office", "easy",   "Ofis kira sözleşmemiz gelecek yıl yenileniyor."),
    ("office", "medium", "Yeni ürün lansmanı için influencer pazarlama bütçesi iki milyon lira olarak onaylandı."),
    ("office", "hard",   "Kurumsal risk değerlendirmesinde operasyonel, finansal ve stratejik riskler önceliklendirildi."),
    ("office", "medium", "Agile çerçevesinde product owner'ın backlog grooming yapması gerekiyor."),
    ("office", "easy",   "Konferans aramasına katılmak için davet linkine tıklayın."),
    ("office", "hard",   "Yatırım bankası roadshow sürecinde on iki kurumsal yatırımcıyla birebir toplantı yapıldı."),
    ("office", "medium", "Human Resources departmanı performans değerlendirmesini 360 derece geri bildirim modeline taşıdı."),
    ("office", "hard",   "KVKK kapsamında veri işleme envanteri hazırlanıp Kişisel Verileri Koruma Kurumu'na bildirildi."),
    ("office", "medium", "Operasyonel verimlilik için Lean Six Sigma metodolojisi uygulanmaya başlandı."),
    ("office", "easy",   "Yeni çalışanın bilgisayarı ve kurumsal emaili oluşturuldu."),
    ("office", "hard",   "Hisse devir işlemi tamamlanmadan önce escrow hesabına kapora tutarı yatırıldı."),
    ("office", "medium", "Müşteri segmentasyonu için RFM analizi yaparak yüksek değerli müşterileri belirledik."),
    ("office", "hard",   "Şirketin WACC'ı yüzde on dörtten yüzde on bire düştü, bu sermaye maliyetinde iyileşme anlamına geliyor."),
    ("office", "medium", "Satış tahminleri için gradient boosting modeli üretimde yüzde seksen beş doğruluk sağlıyor."),
    ("office", "easy",   "Ofiste sosyal mesafe kurallarına uymak zorunlu."),
    ("office", "hard",   "Çok yıllı bütçeleme modelinde enflasyon düzeltmesi için GDP deflatör kullandık."),
    ("office", "medium", "Yeni pazara giriş stratejisi için Porter'ın beş güç analizi yapıldı."),
    ("office", "medium", "Proje zaman çizelgesi Gantt chart formatında MS Project'te hazırlandı."),
    ("office", "hard",   "Sendika ile toplu iş sözleşmesi görüşmelerinde ücret zammı tartışması kritik aşamaya geldi."),
    ("office", "easy",   "Müşteri şikayetini CRM sistemine kaydetmeyi unutma."),
    ("office", "hard",   "Kurumsal yapılanma kapsamında holding altında üç operasyonel şirket kurulacak ve vergi optimizasyonu planlandı."),
    ("office", "medium", "Yıl sonu provizyon hesaplamalarını finansal tablolara yansıtmadan önce auditor'a onaylattık."),
    ("office", "medium", "Çalışan rotasyon programı ile departmanlar arası bilgi transferi sağlanıyor."),
    ("office", "hard",   "Akreditasyon süreci için ISO 27001 kapsamında bilgi güvenliği yönetim sistemi kuruldu."),
    ("office", "easy",   "Toplantı odası salı öğleden sonra için rezerve edildi."),
    ("office", "medium", "Dijital pazarlama ajansıyla ROAS hedefini dört olarak belirledik."),
    ("office", "hard",   "Bağlı şirketlerin konsolidasyon eliminasyonları intercompany işlemler bazında yapılıyor."),
    ("office", "medium", "İş geliştirme ekibi pipeline'da yüz yirmi milyon dolarlık fırsat takip ediyor."),
    ("office", "easy",   "İnsan kaynakları politika kılavuzu tüm çalışanlara dağıtıldı."),
    ("office", "hard",   "Şirket değerlemesinde EV/EBITDA çarpanı sektör ortalamasının üzerinde çıktı."),
    ("office", "medium", "Müşteri onboarding süreci kırk sekiz saatten yirmi dört saate indirildi."),
    ("office", "medium", "Tedarik zinciri görünürlüğü için IoT sensör verilerini ERP'ye entegre ettik."),
    ("office", "hard",   "Garanti kapsamı dışı kalan ürün iadelerinde hukuki süreç TKHK madde on bir kapsamında yürütülüyor."),
    ("office", "easy",   "Çalışma saatlerini değiştirmek için insan kaynakları ile görüşün."),
    ("office", "hard",   "Senaryo analizi kapsamında baz, iyimser ve kötümser olmak üzere üç finansal model hazırlandı."),
    ("office", "medium", "Şirket içi iletişimi güçlendirmek için Slack yerine Microsoft Teams'e geçtik."),
]


async def _seed() -> None:
    from .storage import get_sentences_count, DB_PATH
    import aiosqlite

    count = await get_sentences_count()
    if count > 0:
        logger.info("Sentences table already has %d rows, skipping seed.", count)
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "INSERT INTO sentences (domain, difficulty, text) VALUES (?, ?, ?)",
            SENTENCES,
        )
        await db.commit()

    logger.info("Seeded %d training sentences.", len(SENTENCES))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_seed())
