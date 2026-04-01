# Türkiye Mid-Market Satış Rehberi (Banka Öncesi Adım)

> Araştırma tarihi: 2026-04-01  
> Hedef segment: Vestel, Arçelik, Pegasus, Türk Telekom gibi banka dışı orta-büyük Türk şirketleri

Banka için gereken uyum yolculuğuna girmeden önce referans müşteri kazanmak için minimum gereksinimler.

---

## Zorunlu Olanlar

| Gereksinim | Durum | Maliyet |
|---|---|---|
| Ltd. Şti. kuruluşu | Zorunlu | 10-20K TL (tek sefer) |
| E-fatura sistemi | Pratik zorunlu | 300-800 TL/ay |
| Muhasebeci | Pratik zorunlu | 2-5K TL/ay |
| Yazılım Lisans Sözleşmesi | Zorunlu | Avukat 5-15K TL |
| KVKK Aydınlatma Metni + DPA şablonu | Zorunlu | Aynı avukata ekle |

**VERBİS:** 50 kişiden az, 100M TL altındaysa kayıt zorunlu değil.  
**ISO 27001:** Başlangıçta gerekmez — ihale değil doğrudan satışta neredeyse hiç talep edilmez.  
**Mesleki sorumluluk sigortası:** Yasal zorunluluk yok. Müşteri talep ederse 5-20K TL/yıl.

**Toplam başlangıç maliyeti: ~30-60K TL (tek sefer) + 5-10K TL/ay**

---

## KVKK — On-Premise Avantajı

VoiceFlow'un on-premise modeli burada güçlü bir argüman:

- "Sesiniz hiçbir zaman sizin sunucularınızdan çıkmaz" → BT müdürlerinin büyük bölümünü tatmin eder
- Müşteri Veri Sorumlusu, VoiceFlow Veri İşleyen — on-premise'de bile bu ilişki kısadır
- DPA kısa tutulabilir: "Veri müşteri sunucusunda kalır, yazılım sağlayıcı kişisel veriye erişmez"

---

## Sözleşme Paketi (Minimum)

1. **Yazılım Lisans Sözleşmesi** — kaynak kod sende, sorumluluk sınırlaması (yıllık bedel kadar), yürürlük hukuku Türkiye / İstanbul Mahkemeleri
2. **DPA / KVKK eki** — on-premise için kısa versiyon yeterli
3. **SLA** — yanıt süreleri (kritik hata: 4-8s, diğer: 1 iş günü), destek kanalı, güncelleme kapsamı

---

## Fiyatlandırma Modeli

Türkiye'de en kolay satan yapı: **Kurulum ücreti (tek sefer) + yıllık kullanıcı başı lisans**

Örnek:
- Kurulum: 50K TL (tek sefer)
- Lisans: 5K TL/kullanıcı/yıl veya 100K TL/yıl site lisansı (50 kullanıcıya kadar)
- Yıllık peşin ödeyene %10-15 indirim → Türk şirketler bunu sever (döviz riski, bütçe döngüsü)

---

## Satış Süreci

```
Hafta 1-2:   Demo — BT Müdürü veya CIO birincil muhatap
Hafta 2-6:   Ücretsiz POC/pilot — en güçlü kapı açıcı
Hafta 4-8:   Tedarikçi kaydı — en uzun bürokratik adım (Koç/Arçelik'in ayrı portalı var)
Hafta 6-10:  Sözleşme müzakeresi — hukuk departmanına gider
Hafta 10-16: Bütçe onayı — CFO veya GM, 100K TL+ için şart
Toplam: 2-4 ay tipik
```

**Karar vericiler:**
- BT/IT Müdürü veya CIO → teknik onay
- İlgili birim müdürü (çağrı merkezi, operasyon) → gerçek ihtiyaç sahibi, genellikle bütçe sahibi
- CFO/Genel Müdür → büyük meblağlarda son onay

---

## Sertifikasız Güven İnşası

1. **Ücretsiz 30-60 gün POC** — somut ROI ile dön ("toplantı tutanakları %70 daha hızlı yazılıyor")
2. **İlk 3 müşteriye indirim**, karşılığında referans mektubu + logo kullanım hakkı
3. **Teknik doküman paketi** — güvenlik politikası + mimari diyagram + deployment guide (2-3 sayfa her biri yeter)
4. **Kişisel ağ > soğuk satış** — doğru kişiyle tanışmak 3 aylık süreci 2 haftaya indirir
   - Bilişim Zirvesi, IDC Türkiye, Dijital Türkiye Zirvesi iyi platformlar
5. **Teknokent üyeliği** — "startup garajı" imajını kırar + KDV ve Kurumlar Vergisi muafiyeti

---

## Mid-Market → Banka Geçiş Stratejisi

2-3 mid-market referans müşteri al → banka görüşmesinde "finans dışı kurumsal deneyim" olarak kullan → ISO 27001 sürecini bu gelirle finanse et → bankaya git.

| | Mid-market | Banka |
|---|---|---|
| Süre | 2-4 ay | 6-18 ay |
| ISO 27001 | Gerek yok başlangıçta | Fiilen zorunlu |
| Pentest | İstenirse göster | Zorunlu |
| Uyum başlangıç maliyeti | 30-60K TL | 300K TL+ |
| Karar mercii | BT Müdürü + GM | CISO + Satın Alma Komitesi |

Banka uyum gereksinimleri için: `docs/turkey-enterprise-compliance.md`
