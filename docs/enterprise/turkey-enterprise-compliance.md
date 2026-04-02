# Türkiye Kurumsal Satış — Regülasyon ve Uyum Rehberi

> Araştırma tarihi: 2026-04-01

Türk bankalara (Akbank, Garanti, İş Bankası vb.) ve kamu kurumlarına satışta gereken yasal zorunluluklar, sertifikasyonlar ve vendor onboarding süreci.

---

## KVKK

- Ses kaydı potansiyel olarak **biyometrik veri** = özel nitelikli kişisel veri (KVKK md. 6)
- Transkript metni = standart kişisel veri
- On-premise model → veri dışarı çıkmaz → en büyük KVKK riskini sıfırlar
- VoiceFlow rolü: **Veri İşleyen** (data processor); banka Veri Sorumlusu

**VERBİS kaydı:** Teknik eşik (50 çalışan / 100M TL ciro) altında olsak da ses verisi işlediğimiz için başlangıçtan itibaren kayıt ol. Cezalar 115K–9.2M TL. → https://verbis.kvkk.gov.tr

**Her müşteri ile Veri İşleme Sözleşmesi (DPA) zorunlu:**
- Denetim hakkı (bankanın bizi denetleyebilmesi)
- 72 saat içinde ihlal bildirimi
- Veri silme / iade yükümlülüğü
- Alt işleyenler listesi + onay mekanizması
- Yurt dışı aktarım yasağı beyanı

---

## BDDK

**Temel mevzuat:** Bankaların Bilgi Sistemleri ve Elektronik Bankacılık Hizmetleri Hakkında Yönetmelik (15 Mart 2020, yürürlük 1 Ocak 2021)

- Bankalar birincil/ikincil sistemleri yurt dışına taşıyamaz → on-premise güçlü BDDK argümanı
- Public cloud (AWS/Azure) birincil sistem için yasak
- Tedarikçiden beklenenler: ISO 27001, yıllık pentest, BCP/DRP, güvenli SDLC, Türkiye'de destek ekibi

### Akbank'ın İsteyeceği Belgeler

| Belge | Öncelik |
|---|---|
| ISO 27001 sertifikası | Kritik — yoksa görüşme ilerlemez |
| Penetrasyon testi raporu (son 12 ay, bağımsız firma) | Zorunlu |
| KVKK / VERBİS belgesi | Zorunlu |
| Veri İşleme Sözleşmesi (DPA) taslağı | Zorunlu |
| BCP / DRP planları | Zorunlu |
| Güvenlik politikaları dokümanı | Zorunlu |
| Yazılım mimari dokümanı | Zorunlu |
| Şirket mali tabloları (son 3 yıl) | Zorunlu |
| Referans müşteri listesi (finans sektöründen) | Güçlü avantaj |

---

## ISO 27001

Büyük Türk bankasına satmak için fiilen zorunlu (yasal değil, pratik olarak).

| Aşama | Süre | Maliyet |
|---|---|---|
| Gap analizi | 1-2 ay | 50-150K TL |
| BGYS kurulumu | 3-6 ay | iç kaynak + danışman |
| Sertifikasyon denetimi (Aşama 1+2) | 1-2 ay | 80-200K TL |
| **Toplam** | **6-12 ay** | **150-400K TL** |

TÜRKAK akreditasyonlu kurumlar: BSI, TÜV SÜD, Bureau Veritas Türkiye.

**Kamu ihaleleri için ek:** ISO 27001 + TS ISO/IEC 15504 Seviye 2 veya CMMI Seviye 3 → yazılım yetki belgesi zorunlu.

---

## TÜBİTAK Destekleri

| Program | Bütçe | Oran | Süre | Not |
|---|---|---|---|---|
| **1507 KOBİ Ar-Ge** | Max 3M TL | %75 hibe | 18 ay | VoiceFlow için biçilmiş kaftan |
| **1711 YZ Ekosistem** | Büyük | — | — | Fintech+NLP örtüşüyor; 2025 çağrısı kapandı, 2026'da tekrar |
| **1511 Öncelikli Alanlar** | Çok büyük | — | Uzun | Üniversite + kurum konsorsiyumu |

Başvuru: https://eteydeb.tubitak.gov.tr

---

## Yerli Malı / TÜR Belgesi

- Sanayi ve Teknoloji Bakanlığı, ticaret/sanayi odası aracılığıyla başvuru, 2-3 ay
- Kamu ihalelerinde %15'e kadar fiyat avantajı
- Özel bankalar için tek başına yeterli değil ama eşit rekabette öne geçirir

---

## Vendor Onboarding Süreci

Büyük Türk bankasında ortalama **6-18 ay:**

```
Ay 1-2:   Demo, RFI (Bilgi Talebi)
Ay 2-4:   RFP, teknik şartname hazırlığı
Ay 3-5:   Güvenlik denetimi, sertifika değerlendirmesi
Ay 4-6:   Hukuki inceleme, sözleşme müzakeresi
Ay 5-8:   PoC / pilot uygulama
Ay 7-18:  Satın alma komitesi, üst yönetim onayı, imza
```

---

## Şirket Yapısı

| | Ltd. Şti. | A.Ş. |
|---|---|---|
| Asgari sermaye | 50K TL | 250K TL |
| Kuruluş | Hızlı, ucuz | Yavaş, pahalı |
| Bankalar | Yeterli | Tercih edilen |
| Yatırımcı / hisse | Zor | Zorunlu |

**Strateji:** Şimdi Ltd. Şti., ilk büyük müşteri / yatırım öncesi A.Ş.'ye dönüştür.

---

## Eylem Planı

| Öncelik | Aksiyon | Süre | Maliyet |
|---|---|---|---|
| 🔴 1 | KVKK uyum + VERBİS kaydı | 1-2 ay | 30-80K TL |
| 🔴 2 | DPA şablonu hazırla (avukat) | 1 ay | avukat ücreti |
| 🔴 3 | ISO 27001 gap analizi başlat | 1-2 ay | 50-150K TL |
| 🟡 4 | Penetrasyon testi | 1 ay | 30-80K TL |
| 🟡 5 | ISO 27001 sertifikasyonu al | 6-12 ay | 150-400K TL |
| 🟢 6 | TÜBİTAK 1507 başvurusu | çağrıya göre | — (hibe) |
| 🟢 7 | TÜR Belgesi | 2-3 ay | 10-30K TL |
| 🟢 8 | Ltd → A.Ş. dönüşümü | banka öncesi | 20-50K TL |
