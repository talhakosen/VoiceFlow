# Fine-Tuned Model — Güvenlik & Deployment Analizi

## Deployment Senaryoları

### Seçenek A — On-Premise
```
Müşteri server'ı:
  ├── Qwen 7B base  ← HuggingFace'den indirir (zaten public)
  └── adapter.safetensors  ← bizden gelir (~5MB)
```
Müşteri adapter dosyasına sahip. Kopyalayabilir, başka yerde kullanabilir.

### Seçenek B — Fused Model
```
mlx_lm.fuse → tek model dosyası (~4GB)
  → Private HuggingFace repo'ya koy
  → Müşteri pull eder, server'da çalıştırır
```
On-premise ile aynı risk profili. Müşteri model ağırlıklarına sahip.

### Seçenek C — SaaS/API Modu (en güvenli)
```
Bizim RunPod server'ı:
  └── Fine-tuned model çalışıyor

Müşteri uygulaması → API call → sadece text döner
```
Model ağırlıkları müşteriye hiç gitmiyor. Gerçek IP koruması.

---

## Training Data Gizliliği

**Soru:** Adapter dosyasından eğitim datasını çıkarabilirler mi?

**Cevap: Hayır, pratik olarak imkânsız.**

- Adapter = floating point sayı matrisleri (gradient güncellemeleri)
- "antrowpik → Anthropic düzelt" gibi kurallar adapter'da saklanmıyor
- Sadece ağırlık değişimleri var — orijinal cümleler yok
- Membership inference attack teorik olarak mümkün ama kurumsal müşteri seviyesinde anlamsız

---

## Risk Tablosu

| Varlık | Çalınabilir mi? | Not |
|---|---|---|
| Eğitim datasının kendisi (.jsonl) | ❌ Hayır | Bizim server'da kalır |
| Adapter'dan training data çıkarma | ❌ Pratik değil | Gradient ≠ data |
| Adapter'ı başka modelde kullanma | ⚠️ Teorik | Base model uyuşmazlığı |
| Adapter'ı rakibe verme | ⚠️ Mümkün | Ama değeri sınırlı |
| Sistem prompt'u okuma | ✅ Asıl risk | Kod açık kaynak ise görünür |

**Asıl IP:** Training data değil — **prompt mühendisliği + pipeline + UX.**

---

## Müşteri Segmentine Göre Öneri

| Müşteri | Model | Gerekçe |
|---|---|---|
| Demo / küçük | On-premise, adapter gönder | Kabul edilebilir risk |
| Orta ölçekli | Fused model, private repo | Kurulum kolaylığı |
| Büyük kurumsal | API modu (SaaS) | Model bizde kalır, KVKK uyumlu |
| Müşteriye özel | Adapter per-tenant (K4.5) | Kendi datasıyla kendi server'ında |

---

## GPU Maliyet Analizi

### SaaS Model (biz hostlarız)
```
RunPod RTX 4090 always-on : ~$535/ay
Serverless (pay-per-use)  : 100 kullanıcı × 50 dikte/gün × 0.5s = ~$52/ay
→ Kullanıcı başına ~$0.52/ay GPU maliyeti — per-user lisansla karşılanır
```

### Hız Karşılaştırması
| Senaryo | Gecikme |
|---|---|
| Local MLX (Mac) | ~300ms |
| Müşteri intranet server | ~305ms |
| RunPod EU (TR→EU) | ~340ms |
| Hetzner Türkiye | ~310ms |

Fark kullanıcı için hissedilmez — Whisper zaten 1-3s sürüyor.

### Tier Önerisi
| Segment | Altyapı | Biz ne yaparız |
|---|---|---|
| Küçük (1-20 user) | Bizim SaaS cloud | GPU maliyeti taşırız, marj var |
| Orta (20-200 user) | Hibrit: Whisper Mac, LLM cloud | Paylaşımlı GPU, düşük maliyet |
| Büyük kurumsal | Tam on-premise | Yüksek lisans, sıfır GPU maliyeti |

---

## Katman 4.5 — Müşteriye Özel Adapter (Killer Feature)

Her büyük müşteri için:
1. NDA imzalanır → müşterinin codebase/dökümanlarına erişim
2. `ingest_folder()` ile knowledge base indexlenir (ChromaDB — zaten var)
3. Fine-tune: müşterinin jargonu, kısaltmaları, iç terimleri
4. Adapter müşterinin kendi server'ında çalışır
5. Veri müşterinin sınırlarından çıkmaz → KVKK doğal uyum

```
Genel VoiceFlow adapter (bizden)
  + Akbank bankacılık terimleri, codebase yorumları (NDA kapsamında)
  = "Akbank VoiceFlow" — sadece onlara ait, kimseyle paylaşılmaz
```

**Satış pitch'i:**
> "Akbank'ın iç sistemlerini, kredi terminolojisini, müşteri hizmetleri scriptlerini anlayan bir model.
> Başka hiçbir müşterimizle paylaşmıyoruz. Sizin intranette çalışıyor, veri dışarı çıkmıyor."

**Neden güçlü:**
- Her büyük müşteri = ayrı adapter = ayrı gelir kolu
- Switching cost çok yüksek (model müşteriye adapte olmuş)
- KVKK doğal uyum (veri kendi serverında)
- Örnek hedefler: Akbank, Turkcell, THY, Tümsele, Garanti
