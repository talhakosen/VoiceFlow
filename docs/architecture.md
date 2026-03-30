# VoiceFlow — Sistem Mimarisi

## Mevcut Durum (v0.1, Çalışıyor)

```
[Mac — Apple Silicon]
├── Swift Menu Bar App
│   ├── HotkeyManager  (Fn double-tap → kayıt başlat/durdur)
│   ├── BackendService (HTTP client → localhost:8765)
│   ├── PasteService   (Clipboard + CGEvent Cmd+V)
│   └── MenuBarController (UI + flow koordinasyonu)
│
└── Python Backend (FastAPI, port 8765)
    ├── AudioCapture   (sounddevice, 16kHz mono float32)
    ├── WhisperTranscriber (mlx-whisper, Apple Silicon MLX)
    └── LLMCorrector   (mlx-lm, Qwen 2.5 7B 4-bit, isteğe bağlı)
```

**Doğrulanmış özellikler:**
- Tamamen local, internet bağlantısı yok
- Apple Silicon MLX ile GPU hızlandırması
- Fn double-tap hotkey (push-to-talk + toggle)
- Auto-paste (Accessibility permission gerekli)
- Türkçe + İngilizce + otomatik dil algılama
- LLM düzeltme isteğe bağlı (~4GB, açıkken)
- Yanıt süresi: ~0.5s (LLM kapalı), ~3.5s (LLM açık)

---

## Hedef Mimari (v1.0, Kurumsal)

### İki Deployment Modu

#### Mod A: Local (Bireysel / Küçük Ekip)
```
[Mac]
├── Swift App (thin client)
└── Python Backend (localhost)
    ├── faster-whisper veya mlx-whisper
    ├── Ollama (7B model, local)
    └── ChromaDB (local vector store)
```
- Tüm modeller Mac'te
- İnternet gerekmez
- Şu anki mimarinin geliştirilmişi

#### Mod B: Server (Kurumsal, On-Premise)
```
[Mac — Thin Client]                    [Şirket Sunucusu]
├── Swift App                    →     ├── FastAPI Backend
│   ├── Ses kaydı (local)   HTTPS+VPN  ├── faster-whisper (GPU)
│   ├── Server URL config              ├── vLLM veya Ollama (LLM)
│   └── API Key auth                   ├── ChromaDB (knowledge base)
│                                      ├── Auth middleware
│                                      └── Audit log
│
[VPN] ← Şirket IT altyapısı
```
- Mac sadece ses kaydeder, işleme sunucuda
- Veri şirket ağından dışarı çıkmaz
- Tek sunucu, tüm ekip kullanır
- Docker Compose ile kurulum

---

## Neden Bu Mimari?

### Neden Local-First?
- Türkiye'deki büyük firmalar (Akbank, Türkcel vb.) ses verisi için veri egemenliği ister
- Qwen, Llama gibi modeller açık kaynak → kendi sunucunda çalıştırabilirsin
- Cloud API'ya (OpenAI, Anthropic) veri gönderme → kurumsal müşteri kabul etmez

### Neden Server Modu?
- Her Mac'e 7B+ model (4–10GB) indirmek pratik değil
- Sunucuda model sürekli VRAM'de yüklü → soğuk başlatma yok
- Merkezi güncelleme, merkezi knowledge base

### Neden MLX değil NVIDIA (server için)?
- MLX sadece Apple Silicon — RunPod ve şirket sunucuları NVIDIA kullanır
- faster-whisper + vLLM: NVIDIA GPU'da production-proven
- Apple Silicon Mac client + NVIDIA server: hibrit çalışır

---

## Bileşenler Karşılaştırması

| Bileşen | Local (Mac) | Server (NVIDIA) |
|---|---|---|
| Transkripsiyon | mlx-whisper small | faster-whisper large-v3 |
| LLM | mlx-lm Qwen 7B | vLLM / Ollama Qwen 7B–70B |
| Vector DB | ChromaDB (local) | ChromaDB / Qdrant |
| Auth | Yok (localhost) | API Key + JWT |
| Storage | RAM (geçici) | SQLite + network volume |

---

## Veri Akışı (Server Modu)

```
1. Kullanıcı Fn'e basıyor
2. Mac → POST /api/start (API key header)
3. Ses kaydı başlıyor (Mac'te local)
4. Kullanıcı Fn bırakıyor
5. Mac → POST /api/stop (ses verisi body'de)
6. Sunucu:
   a. faster-whisper → ham metin (~0.3s)
   b. ChromaDB retrieval → ilgili context (~0.1s)
   c. LLM → context-aware düzeltme/format (~0.7s)
7. Sunucu → TranscriptionResponse (text, raw_text, language)
8. Mac → Clipboard → Cmd+V paste
```

**Toplam hedef süre: < 2 saniye (LAN üzerinde)**

---

## Güvenlik Katmanları

1. **VPN** — Şirket ağına erişim şartı (IT tarafından yönetilir)
2. **API Key** — Her request header'da, kullanıcıya özel
3. **HTTPS** — TLS, sunucu sertifikası
4. **Audit Log** — Kim, ne zaman, kaç saniye kaydetti
5. **On-Premise** — Veri şirket sunucusundan çıkmaz

---

## Kısıtlar ve Bilinen Sorunlar (Doğrulanmış)

- Fn key release eventi macOS'ta güvenilmez → double-tap + Force Stop fallback
- Her Swift binary değişikliği Accessibility iznini sıfırlar
- MLX thread-safe değil → tek executor (server modunda bu sorun yok)
- Küçük LLM'ler (1.5B, 3B) Türkçe'de hallüsinasyon yapar → minimum 7B
- RunPod serverless cold start 30–60s → always-on worker gerekli
