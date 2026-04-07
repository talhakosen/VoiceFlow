# VoiceFlow -- Turkiye GPU Sunucu Barindrma Secenekleri

> Surum: 1.0 | Tarih: 2026-04-07 | Hedef: Model D (Hosted TR) ve Model A (On-Prem) icin GPU altyapi secimi

## Amac

VoiceFlow'un Turkiye'deki kurumsal musterilere hizmet verebilmesi icin KVKK/BDDK uyumlu, Turkiye'de fiziksel olarak bulunan GPU sunucu altyapisi gerekiyor. Bu dokuman mevcut secenekleri, maliyetleri ve ticari tavsiyeleri icerir.

## Gereksinimler

| Gereksinim | Detay |
|---|---|
| GPU | Min 1x RTX 4090 (24GB), ideal A100 (80GB) |
| CPU | Min 16 core (inference icin yeterli) |
| RAM | Min 64GB (Whisper + Qwen + FastAPI + OS) |
| Disk | Min 500GB NVMe SSD (modeller + SQLite + loglar) |
| Network | Min 1 Gbps, dusuk latency |
| OS | Ubuntu 22.04+ veya Rocky Linux 9 |
| Docker | Docker Engine + Docker Compose v2 |
| Fiziksel konum | Turkiye Cumhuriyeti sinilari icinde (KVKK/BDDK zorunlulugu) |
| SLA | Min %99.9 uptime |

---

## 1. Turk GPU Hosting Saglayicilari (Dedicated Server)

### 1.1 Cloudvist

- **Web:** https://cloudvist.com/gpu-sunucu/
- **GPU secenekleri:** RTX 4090, A100, H100, RTX 5090
- **DC:** Turkiye, Tier III+
- **Teslimat:** 24 saat icinde hazir
- **Fiyat:** Web'de acik fiyat yok, teklif bazli
- **Tahmini maliyet:** RTX 4090 dedicated ~$400-600/ay (piyasa ortalamasi)
- **Not:** AI/ML odakli, Turk sirketi

### 1.2 HOSTKEY Turkiye

- **Web:** https://hostkey.com/dedicated-servers/turkey/
- **GPU secenekleri:** RTX 4090, A100 80GB, A4000, A5000, A6000
- **DC:** Istanbul, Tier III
- **Fiyat (referans):** A100 80GB ~EUR1.53/saat (~EUR1,100/ay), RTX 4090 ~EUR0.50/saat (~EUR360/ay)
- **Billing:** Saatlik ve aylik secenekler
- **Not:** Hollanda merkez, Istanbul DC var. KVKK icin DPA gerekir.

### 1.3 Oweb

- **Web:** https://www.oweb.net.tr/en/gpu-dedicated-server
- **DC:** Istanbul, Tier III sertifikali
- **Network:** 2x10Gbit Turk Telekom + 2x10Gbit Turkcell Superonline
- **GPU secenekleri:** NVIDIA lineup (detay icin teklif gerekli)
- **Not:** Turk sirketi, operator-redundant ag altyapisi

### 1.4 Cpunow

- **Web:** https://cpunow.com/gpu-sunucu
- **RTX 4090 paketi:** EPYC 7282 + 256GB RAM + 1TB NVMe + RTX 4090 = 5,499 TL/ay (~$165/ay)
- **Not:** Cok uygun fiyat, SLA ve DC Tier seviyesi dogrulanmali

### 1.5 Weridata

- **Web:** https://www.weridata.com.tr/ekran-kartli-sunucu
- **GPU secenekleri:** RTX 3060, 3080, 4090, Quadro serisi
- **DC:** Turkiye, Tier III+
- **Baslangic fiyat:** Quadro RTX 4000 1,500 TL/ay'dan baslayan fiyatlar
- **vGPU:** Paylasimli GPU secenegi (dusuk maliyet)
- **Not:** RDP/Parsec erisim, Windows/Linux

### 1.6 Upcell

- **Web:** https://upcell.com.tr/ekran-kartli-sunucu/
- **GPU secenekleri:** RTX 3060, 3080, 4090
- **DC:** Turkiye, Tier 3
- **Fiyat:** Teklif bazli
- **Not:** Turk sirketi

### 1.7 Adahost

- **Web:** https://adahost.net/en/gpu-server
- **DC:** Kuzey Data Center, Istanbul
- **GPU:** NVIDIA vGPU (A5000 bazli)
- **Not:** CUDA destekli, AI/ML uyumlu, fiyat teklif bazli

### 1.8 Febzen

- **Web:** https://febzen.com/gpu-sunucu-kirala
- **GPU secenekleri:** H100, A100, multi-GPU cluster
- **Not:** Ozel AI projeleri icin konfigurasyonlar

---

## 2. Colocation (Kendi Donanim)

Kendi GPU workstation'imizi (orn. RTX 4090 + EPYC/Ryzen) bir TR veri merkezine yerlestirme.

### Colocation Saglayicilari

| Saglayici | DC | Tier | 1U Aylik | 2U Aylik | 4U Aylik |
|---|---|---|---|---|---|
| Kuzey DC | Istanbul | III | ~3,000 TL | ~4,500 TL | ~7,000 TL |
| Verigom | Istanbul | III | ~2,500 TL | ~3,500 TL | teklif |
| Meric.net | Istanbul | III | teklif | teklif | teklif |
| AnadoluHost | Istanbul (Telehouse) | III+ | ~2,500 TL | ~4,000 TL | teklif |
| NiobeHosting | Istanbul | III | ~2,000 TL | ~3,500 TL | teklif |
| Hosting.com.tr | Istanbul | III | teklif | teklif | teklif |

**GPU workstation maliyeti (tek seferlik):**
- RTX 4090 (24GB): ~45,000-55,000 TL (~$1,350-1,650)
- AMD EPYC / Ryzen 9: ~15,000-25,000 TL
- 64GB ECC RAM: ~8,000-12,000 TL
- 1TB NVMe: ~3,000-5,000 TL
- Kasa + PSU (850W+): ~5,000-10,000 TL
- **Toplam:** ~80,000-110,000 TL (~$2,400-3,300)

**Colocation + donanim toplam (ilk yil):**
- Donanim: ~100,000 TL (tek seferlik)
- Colocation: ~36,000-54,000 TL/yil (2U, 3,000-4,500 TL/ay)
- **Toplam ilk yil:** ~136,000-164,000 TL (~$4,100-4,900)
- **Sonraki yillar:** ~36,000-54,000 TL/yil (sadece colocation)

---

## 3. Hetzner

- **Turkiye DC'si:** YOK. Hetzner'in Turkiye'de veri merkezi bulunmuyor.
- **En yakin:** Almanya (Nuremberg, Falkenstein), Finlandiya (Helsinki)
- **GPU sunucu:** GEX131 (RTX PRO 6000 Blackwell) EUR889/ay, GEX44 (RTX 4090) EUR219/ay
- **KVKK/BDDK:** UYGUN DEGIL. Veri Turkiye disinda kalir. BDDK kapsamindaki kurumlar icin kullanilamaz.
- **Kullanim alani:** Sadece gelistirme/test, production degil.

---

## 4. Hyperscaler'lar (AWS / Azure / GCP)

### AWS Turkiye

- **Region:** YOK. En yakin: eu-south-1 (Milano), me-south-1 (Bahreyn)
- **GPU instance:** p4d (A100), p5 (H100) mevcut ama TR region yok
- **BDDK:** UYGUN DEGIL (veri yurt disinda)

### Azure Turkiye

- **Region:** YOK. En yakin: West Europe (Hollanda), UAE North
- **Not:** Azure'un Turkiye region planlari bilinmiyor
- **BDDK:** UYGUN DEGIL

### GCP Turkiye

- **Region:** YOK. En yakin: europe-west1 (Belcika)
- **BDDK:** UYGUN DEGIL

### Sonuc

Hicbir hyperscaler'in Turkiye'de region'i yok. BDDK kapsamindaki bankalar ve kamu kurumlari icin kullanilmasi yasal olarak mumkun degil. KVKK icin de acik riza + CEYD (Cekirdek Ekonomik Yarar Degerlendirmesi) gerekir ki bu pratik degil.

---

## 5. RunPod / Lambda Labs

| Saglayici | TR Lokasyonu | En Yakin | Not |
|---|---|---|---|
| RunPod | YOK | EU (Hollanda, Romanya) | 30+ region ama TR yok |
| Lambda Labs | YOK | Sadece ABD | ABD disinda DC yok |
| Vast.ai | YOK | Degisken (P2P) | Guvenilirlik dusuk |

**KVKK/BDDK:** Hicbiri Turkiye'de degil, kurumsal production icin UYGUN DEGIL.

**Mevcut kullanim:** RunPod sadece gelistirme, fine-tuning ve demo icin kullanilmaya devam edecek.

---

## 6. BDDK Veri Lokalizasyon Kurallari

BDDK Yonetmeligi (15.03.2020, Resmi Gazete 31069):

- Bankalarin birincil ve ikincil sistemleri **yurt icinde** bulunmak zorunda
- Veri lokalizasyonu sadece kopya degil, **altyapi + donanim + yazilim** fiziksel olarak TR'de olmali
- Ozel bulut (tek bankaya tahsisli) veya topluluk bulutu modelleri tanimli
- Tedarikci ISO 27001 sertifikasi gerekli (veya planlanmis olmali)

**VoiceFlow icin anlami:** Model A (On-Prem) ve Model D (Hosted TR) tek BDDK-uyumlu secenekler.

---

## 7. Karsilastirma Tablosu

| Secenek | GPU | Aylik Maliyet | KVKK | BDDK | SLA | Oneri |
|---|---|---|---|---|---|---|
| **Cloudvist dedicated** | RTX 4090 / A100 | ~$400-600 | Uyumlu | Uyumlu | %99.9 | Model D icin ARASTIR |
| **HOSTKEY Istanbul** | RTX 4090 / A100 | EUR360-1,100 | DPA ile | DPA ile | %99.9 | Model D icin ARASTIR |
| **Oweb Istanbul** | Cesitli | teklif | Uyumlu | Uyumlu | Tier III | Model D icin ARASTIR |
| **Cpunow** | RTX 4090 | 5,499 TL (~$165) | Uyumlu | Dogrulanmali | ? | FIYAT AVANTAJLI |
| **Colocation (kendi HW)** | RTX 4090 | ~3,000-4,500 TL | Uyumlu | Uyumlu | DC'ye bagli | UZUN VADEDE UCUZ |
| **Hetzner (DE)** | RTX 4090 | EUR219 | RISKLI | UYGUN DEGIL | %99.9 | SADECE DEV/TEST |
| **AWS/Azure/GCP** | A100/H100 | $2,000-5,000 | RISKLI | UYGUN DEGIL | %99.99 | KULLANILAMAZ |
| **RunPod** | RTX 4090 | ~$0.39/saat | RISKLI | UYGUN DEGIL | Yok | SADECE DEV |

---

## 8. Tavsiye

### Kisa Vade (Q2-Q3 2026): Cloudvist veya HOSTKEY Istanbul

1. **Cloudvist** ve **HOSTKEY Istanbul**'dan RTX 4090 dedicated server teklifi al
2. **Cpunow**'dan teklif al (fiyat cok uygun, SLA/DC dogrulanmali)
3. Oweb'den de alternatif teklif al
4. Karsilastirma kriterleri: aylik fiyat, SLA, Docker destegi, network bandwidth, destek kalitesi
5. DPA (Veri Isleme Sozlesmesi) imzalanabilirligini dogrula

**Hedef:** 1x RTX 4090 dedicated server, aylik $200-500 arasi, Model D pilot icin yeterli.

### Orta Vade (Q4 2026+): Colocation

Musteri sayisi artarsa ve maliyet optimizasyonu gerekirse:
1. 1x RTX 4090 workstation topla (~100K TL)
2. Kuzey DC veya Telehouse Istanbul'a yerlestir (~3,000-4,500 TL/ay)
3. 2. yildan itibaren dedicated server'a gore %40-60 tasarruf

### Uzun Vade (2027+): Multi-GPU Colocation

- 2-4x GPU (musteri sayisina gore)
- A100 veya H100 yatirimi (banka musterileri icin)
- Yedekli (redundant) kurulum: 2 farkli DC'de aktif-pasif

---

## 9. Sonraki Adimlar

- [ ] Cloudvist, HOSTKEY Istanbul, Cpunow, Oweb'den resmi teklif iste
- [ ] SLA, DPA, KVKK uyum belgelerini karsilastir
- [ ] Pilot icin 1 saglayici sec ve 1 aylik test yap
- [ ] Docker Compose deployment test et (backend + ollama + whisper)
- [ ] Latency testi: Istanbul DC -> Istanbul ofis (hedef <50ms RTT)
- [ ] Multi-tenant stress test: 10 concurrent kullanici, tek RTX 4090
- [ ] Monitoring stack kur (Prometheus + Grafana veya basit health check)

---

## Kaynaklar

- [Cloudvist GPU Sunucu](https://cloudvist.com/gpu-sunucu/)
- [HOSTKEY Turkiye](https://hostkey.com/dedicated-servers/turkey/)
- [Oweb GPU Dedicated Server](https://www.oweb.net.tr/en/gpu-dedicated-server)
- [Cpunow GPU Sunucu](https://cpunow.com/gpu-sunucu)
- [Weridata GPU Sunucu](https://www.weridata.com.tr/ekran-kartli-sunucu)
- [Upcell Ekran Kartli Sunucu](https://upcell.com.tr/ekran-kartli-sunucu/)
- [Adahost GPU Server](https://adahost.net/en/gpu-server)
- [Febzen GPU Sunucu](https://febzen.com/gpu-sunucu-kirala)
- [Kuzey DC Colocation](https://kuzeydc.com/colocation)
- [Verigom Colocation](https://www.verigom.com/sunucu-barindirma/)
- [Hetzner GPU Server](https://www.hetzner.com/dedicated-rootserver/gex44/)
- [BDDK Yonetmelik](https://www.bddk.org.tr/Mevzuat/Liste/134)
- [Istanbul Data Centers](https://www.datacentermap.com/turkey/istanbul/)
- [Cloud GPU Pricing Comparison](https://getdeploying.com/gpus)
