# Varlık Envanteri

**Belge No:** VF-AST-001  
**Versiyon:** 1.0  
**Tarih:** 2026-04-04  
**Gözden Geçirme:** Yılda bir veya değişiklikte

---

## 1. Yazılım Varlıkları

| ID | Varlık | Konum | Sınıf | Sahibi | Kritiklik |
|---|---|---|---|---|---|
| SW-001 | Backend (Python/FastAPI) | `backend/` — private git repo | Gizli | Geliştirici | Yüksek |
| SW-002 | macOS Swift App | `VoiceFlowApp/` — private git repo | Gizli | Geliştirici | Yüksek |
| SW-003 | ML modelleri (Whisper, Qwen) | `ml/` + HuggingFace `tkosen/voiceflow-whisper-tr` | Gizli | Geliştirici | Yüksek |
| SW-004 | LoRA adapter (fine-tuned) | `ml/qwen/adapters_mlx/` | Gizli | Geliştirici | Yüksek |
| SW-005 | Web sitesi (Next.js) | `web/` — public | Genel | Geliştirici | Düşük |

## 2. Veri Varlıkları

| ID | Varlık | Konum | Sınıf | Sahibi | Kritiklik |
|---|---|---|---|---|---|
| DA-001 | Müşteri ses kayıtları | `~/.voiceflow/voiceflow.db` | Kişisel/Gizli | Müşteri | Kritik |
| DA-002 | Transkripsiyon metinleri | `~/.voiceflow/voiceflow.db` | Kişisel/Gizli | Müşteri | Kritik |
| DA-003 | Audit log | `~/.voiceflow/voiceflow.log` | Gizli | VoiceFlow | Yüksek |
| DA-004 | ISSAI eğitim verisi | `ml/whisper/datasets/issai/` | Genel (lisanslı) | ISSAI | Orta |
| DA-005 | IT eğitim dataseti | `ml/whisper/datasets/it_dataset/` | Gizli | VoiceFlow | Orta |
| DA-006 | Konfigürasyon (`config.yaml`) | Proje kök dizini | İç kullanım | Geliştirici | Yüksek |
| DA-007 | Secrets (`.env`) | Proje kök dizini | Gizli | Geliştirici | Kritik |

## 3. Altyapı Varlıkları

| ID | Varlık | Konum | Sınıf | Sahibi | Kritiklik |
|---|---|---|---|---|---|
| IN-001 | Geliştirici Mac (Apple Silicon) | Fiziksel — İstanbul | İç kullanım | Geliştirici | Yüksek |
| IN-002 | RunPod GPU Pod (eğitim) | RunPod Cloud | İç kullanım | Geliştirici | Orta |
| IN-003 | Müşteri on-premise sunucu | Müşteri sahası | Müşteri | Müşteri | Kritik |

## 4. Üçüncü Taraf Servisleri

| ID | Servis | Kullanım | Veri paylaşımı | Risk |
|---|---|---|---|---|
| TP-001 | HuggingFace | Model barındırma | Model ağırlıkları | Düşük |
| TP-002 | RunPod | GPU eğitim | Eğitim verisi | Orta |
| TP-003 | GitHub | Kaynak kod | Kaynak kodu | Orta |
| TP-004 | Trello | Proje yönetimi | Task notları | Düşük |

## 5. Veri Sınıflandırma

| Sınıf | Tanım | Örnek |
|---|---|---|
| **Kritik** | Kişisel veri, KVKK kapsamında | Ses kaydı, transkripsiyon |
| **Gizli** | İş sırrı, ticari değer taşıyan | Kaynak kodu, ML modelleri, secrets |
| **İç kullanım** | Yetkili personele açık | Config, log dosyaları |
| **Genel** | Kamuya açık | Web sitesi, açık dokümanlar |
