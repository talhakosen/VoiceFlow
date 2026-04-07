# VoiceFlow — RunPod Configs

Pod oluşturmak ve setup yapmak için tek yer.

## Kullanım

```bash
cd runpod/

# Pod oluştur
python create_pod.py issai    # Whisper Stage 1 — ISSAI 164K (H100)
python create_pod.py stage2   # Whisper Stage 2 — noktalama fine-tune (H100)
python create_pod.py qwen     # Qwen LoRA training (RTX 4090)
python create_pod.py ollama   # Ollama inference (RTX 4090)

# Çalışan pod'ları listele
python create_pod.py --list
```

## Workflow: Cloud Inference (RTX 4090, doğrulanan 2026-04-07)

Mac app ses kaydeder → RunPod GPU'da transkripsiyon + düzeltme → sonuç geri döner.
**~850ms toplam** (local MLX ~6sn'den 7x hızlı).

### Mimari

```
Mac App → Local Backend (ses kayıt) → SSH Tunnel → RunPod Pod (GPU)
                                                      ├── faster-whisper large-v3 (transkripsiyon, ~300ms)
                                                      └── Ollama qwen2.5:7b (düzeltme, ~350ms)
                                                   → sonuç geri döner (~850ms toplam)
```

### Benchmark (doğrulanan)

| Yöntem | Ortalama | Açıklama |
|---|---|---|
| Local MLX (Mac) | ~6000ms | whisper-small + Qwen 4-bit |
| RunPod US + proxy + base64 | ~2500ms | İlk deney |
| RunPod EU + proxy + base64 | ~1500ms | Romanya DC |
| **RunPod EU + SSH tunnel + multipart** | **~850ms** | **Aktif config** |

### Latency breakdown

| Katman | Süre |
|---|---|
| Ping İstanbul→Romanya | ~50ms |
| SSH tunnel + HTTP | ~200ms |
| Audio upload (multipart) | ~100ms |
| Whisper GPU (large-v3) | 276-660ms |
| LLM GPU (qwen2.5:7b) | 250-470ms |
| Response | ~50ms |

### Kurulum (sıfırdan)

```bash
# 1. RunPod pod oluştur (EU datacenter, RTX 4090)
#    MCP: mcp__runpod__create-pod ile veya RunPod UI'dan
#    Image: runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04
#    GPU: RTX 4090, Disk: 50GB, Ports: 22/tcp 8765/http 11434/http
#    DC: EU-RO-1 (Romanya — İstanbul'a en yakın)

# 2. SSH ile bağlan ve kur
ssh -p <PORT> root@<IP> 'bash -s' << 'EOF'
set -e
apt-get update -qq && apt-get install -y -qq zstd > /dev/null 2>&1
curl -fsSL https://ollama.com/install.sh | sh
OLLAMA_HOST=0.0.0.0 ollama serve > /tmp/ollama.log 2>&1 &
sleep 5
ollama pull qwen2.5:7b
curl -sf http://localhost:11434/api/generate -d '{"model":"qwen2.5:7b","keep_alive":-1}' > /dev/null
pip install faster-whisper soundfile httpx numpy fastapi uvicorn python-multipart --quiet
# CUDA lib fix (Ollama'nın libcublas'ını system path'e symlink)
ln -sf /usr/local/lib/ollama/cuda_v12/libcublas.so.12 /usr/lib/x86_64-linux-gnu/
ln -sf /usr/local/lib/ollama/cuda_v12/libcublasLt.so.12 /usr/lib/x86_64-linux-gnu/
ldconfig
python3 -c "from faster_whisper import WhisperModel; WhisperModel('Systran/faster-whisper-large-v3', device='cuda', compute_type='float16'); print('OK')"
EOF

# 3. Handler + server yükle
scp -P <PORT> runpod/serverless/handler.py root@<IP>:/root/handler.py
# server.py'yi oluştur (multipart destekli — aşağıya bak)

# 4. Server başlat (pod'da)
ssh -p <PORT> root@<IP> 'nohup python3 /root/server.py > /tmp/server.log 2>&1 &'

# 5. SSH tunnel aç (Mac'te)
ssh -f -N -L 18765:localhost:8765 -p <PORT> root@<IP>

# 6. .env güncelle
# RUNPOD_VOICEFLOW_POD_ID=<pod_id>
# RUNPOD_INFERENCE_URL=http://localhost:18765/inference

# 7. config.yaml güncelle
# whisper:
#   backend: runpod

# 8. Backend restart
./voiceflow.sh restart
```

### Pod restart sonrası (Ollama + server tekrar başlatma)

```bash
ssh -p <PORT> root@<IP> 'bash -s' << 'EOF'
OLLAMA_HOST=0.0.0.0 ollama serve > /tmp/ollama.log 2>&1 &
sleep 5
curl -sf http://localhost:11434/api/generate -d '{"model":"qwen2.5:7b","keep_alive":-1}' > /dev/null
nohup python3 /root/server.py > /tmp/server.log 2>&1 &
EOF
# SSH tunnel yeniden aç (Mac'te)
ssh -f -N -L 18765:localhost:8765 -p <PORT> root@<IP>
```

### Kritik notlar

- **CUDA lib symlink ZORUNLU**: Ollama kendi `libcublas.so.12`'sini `/usr/local/lib/ollama/cuda_v12/` altına koyar. faster-whisper bulamaz → `ln -sf` ile system path'e bağla.
- **SSH tunnel vs proxy**: RunPod proxy (`*.proxy.runpod.net`) ~200ms overhead. SSH tunnel ~50ms. Tunnel her zaman tercih et.
- **Multipart upload**: Base64 JSON yerine raw WAV bytes gönderir — %33 küçük payload, ~40ms kazanç.
- **EU-RO-1 (Romanya)**: İstanbul'a en yakın RunPod DC. Ping ~50ms. US-NC ~150ms.
- **VRAM kullanımı**: Whisper large-v3 (1.5GB) + Ollama qwen2.5:7b (5GB) = 6.5GB / 24GB. 14b modele bile yer var.
- **Maliyet**: RTX 4090 $0.59/saat. Sadece aktif kullanımda açık tut.
- **Local'e geri dönmek**: `config.yaml` → `whisper.backend: ""` + `./voiceflow.sh restart`. Tek satır.

### Dosyalar

```
runpod/serverless/
├── handler.py           ← RunPod serverless handler (audio → Whisper → Ollama → text)
├── Dockerfile           ← Serverless deploy için (Docker image gerektirir)
├── start.sh             ← Serverless startup script
├── deploy.py            ← Serverless endpoint oluşturma yardımcısı
├── requirements.txt     ← Python deps
└── test_input.json      ← Test payload

backend/src/voiceflow/
├── transcription/runpod_transcriber.py   ← Audio → RunPod API → result (multipart + serverless)
└── correction/runpod_passthrough.py      ← No-op corrector (RunPod handles LLM)
```

---

## Workflow: Whisper Stage 2 — Noktalama Fine-Tune

**Base:** `tkosen/voiceflow-whisper-tr` (Stage 1 çıktısı)
**Hedef:** Aynı ISSAI WAV'lar + noktalı text → decoder büyük harf + noktalama öğrenir
**Sonuç:** `voiceflow-whisper-tr-v2`

### Ground Truth Noktalama: Qwen 7B Inline Pipeline

Noktalama **ayrı script değil, `whisper_stage2_finetune.py` içinde otomatik** çalışır:

```
ISSAI WAV+TXT (164K)
    ↓  Qwen 7B fp16 (H100, batch=64, ~15-20 dk)
    ↓  /workspace/punct_cache.json (pod restart'ta yeniden çalışmaz)
    ↓  Qwen unload → GPU temizle
Whisper Stage 2 training (~2 saat)
```

**Neden Qwen 7B fp16 (4-bit değil):**
- H100 80GB VRAM var — Qwen 7B fp16 = ~14GB, rahat sığar
- `bitsandbytes` CUDA 12.1 ile uyumsuz (`libnvJitLink.so.13` eksik) — gereksiz
- Kod daha basit, aynı kalite

**Neden inline (ayrı script değil):**
- Tek komutla: ISSAI indir → Qwen noktalama → Whisper training
- Cache'li: pod restart'ta Qwen tekrar çalışmaz, `punct_cache.json` kullanılır
- Ekstra adım yok, hata yüzeyi küçük

**Tek komut çalıştırma:**
```bash
cd /workspace
HF_TOKEN=hf_xxx nohup python whisper_stage2_finetune.py > stage2.log 2>&1 &
tail -f stage2.log
```

### Çalışan Config (2× OOM'dan sonra doğrulanan — 2026-04-04)

> **batch=32 OOM verir!** `accelerate._convert_to_fp32` eval sırasında VRAM patlatır.
> `gradient_checkpointing=True` + `batch=16` ile stabil — H100'da 10644 step tamamlandı.

| Faktör | Stage 1 | Stage 2 (doğrulanan) |
|---|---|---|
| Epoch | 3 | 2 |
| Batch | 16 | **16** (32 OOM — gradient_checkpointing ile) |
| gradient_checkpointing | ✗ | **✓ ZORUNLU** |
| Workers | 8 | **16** |
| torch.compile | ✗ | **✓ (+20%)** |
| Adam | default | **adamw_torch** (bitsandbytes CUDA 12.1 uyumsuz) |
| prefetch_factor | ✗ | **4** |
| RAM disk | ✗ | **✓ (I/O kaldırır)** |
| bf16_full_eval | ✗ | **✓ ZORUNLU** |

**Gerçek süre: ~2 saat (tek run). OOM crash + resume = ~4.5 saat toplam.**

### RAM disk trick (en büyük kazanım)
ISSAI WAV'lar ~26GB. H100 pod'larında 200GB+ RAM var → WAV'ları RAM'e kopyala, disk I/O'yu sıfırla:
```bash
# ~60 saniye sürer, ~1 saat training kazancı
mkdir -p /dev/shm/issai
cp -r /workspace/issai/extracted /dev/shm/issai/
# script otomatik /dev/shm → /root → /workspace sırasını dener
```

### ISSAI nerede olduğuna göre strateji

| Durum | Aksiyon |
|---|---|
| Stage 1 pod **aynı session** | `/root/issai/extracted` var — sadece script + JSONL yükle |
| **Yeni pod** (Stage 1 pod silindi) | Script otomatik HF'ten indirir, `/workspace/issai/`'a kaydeder |
| Stage 1 pod canlıyken kopyala | `cp -r /root/issai /workspace/issai` → kalıcı volume'a |

### Tam çalıştırma

```bash
# 1. Pod aç
python create_pod.py stage2

# 2. Deps kur (torchvision uyumsuz — kaldır; bitsandbytes gerekmez)
ssh -p <PORT> root@<IP> "pip uninstall -y torchvision && pip install -q 'transformers>=4.44' 'peft>=0.12' soundfile librosa accelerate"

# 3. Script yükle
scp -P <PORT> ../ml/whisper/whisper_stage2_finetune.py root@<IP>:/workspace/

# 4. Başlat (ISSAI indir → Qwen noktalama → Whisper training — tek komut)
ssh -p <PORT> root@<IP> \
  "cd /workspace && HF_TOKEN=hf_xxx nohup python whisper_stage2_finetune.py > stage2.log 2>&1 &"

# 5. Log takip
ssh -p <PORT> root@<IP> 'tail -f /workspace/stage2.log'

# 6. Bittikten sonra pod durdur (HF'e otomatik push eder)
# Model: tkosen/voiceflow-whisper-tr-v2
```

**Deps notu:** `torchvision` torch 2.11+ ile uyumsuz (`torchvision::nms` operatörü yok) → cascade import hatası yapar. Kaldır.

### Bilinen Sorunlar ve Çözümleri

| Hata | Sebep | Çözüm |
|---|---|---|
| `torch.OutOfMemoryError` at eval | `_convert_to_fp32`: eval logitleri fp32'e çevrilince VRAM doldu | `bf16_full_eval=True` + `eval_accumulation_steps=4` + **`gradient_checkpointing=True`** + **`batch=16`** |
| `torch.OutOfMemoryError` at train | batch=32 + LoRA aktivasyonları VRAM'e sığmıyor | `gradient_checkpointing=True` + `batch=16` |
| `bitsandbytes libnvJitLink.so.13` | CUDA 12.1 uyumsuz | bitsandbytes kaldır, `optim="adamw_torch"` kullan |
| `torchvision::nms` missing | torch 2.11+ uyumsuz | `pip uninstall -y torchvision` |
| `cuDNN Frontend error` | cuDNN SDPA | `torch.backends.cuda.enable_cudnn_sdp(False)` |
| DataLoader `rebuild_storage_fd` | `num_workers>0` shared memory | `dataloader_num_workers=0` |
| RunPod UI GPU %0 gösteriyor | UI render engine ölçer, CUDA değil | `nvidia-smi` veya VRAM%'e bak |
| eval sonrası hız yavaş (~70s/it) | torch.compile JIT recompile yapıyor | Normal — 10 step sonra ~1.75s/it'ye döner |

**Checkpoint resume (log adını değiştir — önceki crash logunu korur):**
```bash
RESUME_CHECKPOINT=/root/training_out/whisper_stage2/checkpoint-3000 \
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
HF_TOKEN=hf_xxx nohup python whisper_stage2_finetune.py >> stage2_v3.log 2>&1 &
```

---

## Workflow: Whisper Stage 1 — ISSAI Training

```bash
# 1. Pod oluştur
python create_pod.py issai

# 2. Script + setup yükle (pod IP ve PORT RunPod UI'dan)
scp -P <PORT> ../ml/whisper/whisper_issai_finetune.py root@<IP>:/workspace/
scp -P <PORT> setup/issai.sh root@<IP>:/workspace/

# 3. SSH + kurulum + training başlat
ssh -p <PORT> root@<IP>
export HF_TOKEN=hf_xxx
bash /workspace/issai.sh

# 4. Log takip
tail -f /workspace/training.log

# 5. Bittikten sonra model indir
scp -rP <PORT> root@<IP>:/workspace/voiceflow-whisper-tr ../ml/whisper/
```

## Workflow: Qwen v2 Training — Filler Temizleme

**Yeni:** 496 filler/disfluency pair + 600 existing sample = 1096 pair mixed dataset.
Hedef: şey/yani/hani/işte/ee/aa temizleme + backtrack + stutter + sayı normalizasyonu.

### Çalışan Setup (H100, 2026-04-04 doğrulanan)

> **unsloth kullanma** — torch version hell yaratır. `transformers + peft + trl` direkt stack daha stabil.
> H100 image'ı: `runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04` — torch 2.2.0+cu121 hazır gelir.

```bash
# 1. Pod oluştur — H100 tercih et (3 dk training vs RTX 4090 8 dk)
python create_pod.py qwen   # ya da MCP ile H100 seç

# 2. Deps kur (bir kerelik — ~30 sn)
ssh -p <PORT> root@<IP> "pip install -q 'transformers==4.47.0' 'peft==0.13.0' 'trl==0.13.0' 'accelerate>=0.26' datasets"
# NOT: torchvision kaldırmaya gerek yok (H100 image'ında yok zaten)

# 3. Dataset yükle
scp -P <PORT> ../ml/qwen/datasets/v2/train.jsonl root@<IP>:/workspace/train_v2.jsonl
scp -P <PORT> ../ml/qwen/datasets/v2/valid.jsonl root@<IP>:/workspace/valid_v2.jsonl
scp -P <PORT> ../ml/qwen/scripts/train_runpod_v2_hf.py root@<IP>:/workspace/

# 4. Training başlat (~3 dk H100, ~8 dk RTX 4090)
ssh -p <PORT> root@<IP> "nohup python /workspace/train_runpod_v2_hf.py > /workspace/training_v2.log 2>&1 &"
ssh -p <PORT> root@<IP> "tail -f /workspace/training_v2.log"

# 5. Adapter indir + MLX'e dönüştür
scp -rP <PORT> root@<IP>:/workspace/adapters_v2 ../ml/qwen/adapters_v2_runpod
cd ../ml/qwen/scripts && python convert_adapter.py \
  --input ../../adapters_v2_runpod --output ../../adapters_v2_mlx

# 6. config.yaml güncelle
# llm:
#   adapter_path: ml/qwen/adapters_v2_mlx
```

**Script:** `ml/qwen/scripts/train_runpod_v2_hf.py` (unsloth-free, transformers+peft+trl)
**Training config:** LR=8e-6, MAX_STEPS=400, bf16, adamw_torch, batch=8, grad_accum=2
**Sonuç:** eval_loss=0.71, ~3 dakika H100'de (2026-04-04 doğrulanan)

### Bilinen Sorunlar

| Hata | Sebep | Çözüm |
|---|---|---|
| `unsloth: torch requires upgrade` | unsloth her torch versiyonu için ayrı build ister | **unsloth kullanma** — `train_runpod_v2_hf.py` kullan |
| `torchvision::nms missing` | torchvision farklı torch için compile | `pip uninstall -y torchvision` |
| `transformers 5.x + peft circular import` | peft→transformers→torchao→torch.int1 yok | `transformers==4.47.0` kullan |
| `trl 1.0 requires transformers 5.x` | `is_trackio_available` import | `trl==0.13.0` kullan |

## Workflow: Qwen v1 Training — Orijinal (arşiv)

```bash
# 1. Pod oluştur
python create_pod.py qwen

# 2. Dataset + script yükle
scp -P <PORT> ../ml/qwen/datasets/train.jsonl root@<IP>:/workspace/
scp -P <PORT> ../ml/qwen/datasets/valid.jsonl root@<IP>:/workspace/
scp -P <PORT> ../ml/qwen/scripts/train_runpod.py root@<IP>:/workspace/
scp -P <PORT> setup/qwen.sh root@<IP>:/workspace/

# 3. SSH + çalıştır
ssh -p <PORT> root@<IP>
bash /workspace/qwen.sh

# 4. Adapter indir + dönüştür
scp -rP <PORT> root@<IP>:/workspace/adapters ../ml/qwen/adapters_runpod
cd ../ml/qwen/scripts && python convert_adapter.py
```

## Workflow: Ollama Inference

```bash
# 1. Pod oluştur
python create_pod.py ollama

# 2. SSH + setup
scp -P <PORT> setup/ollama.sh root@<IP>:/workspace/
ssh -p <PORT> root@<IP> 'bash /workspace/ollama.sh'

# 3. .env güncelle
# RUNPOD_OLLAMA_URL=https://<POD_ID>-11434.proxy.runpod.net
```

## Pod Configs

| Config | Kısayol | GPU | Disk | Volume | Süre |
|---|---|---|---|---|---|
| `issai_h100.json` | `issai` | H100 80GB | 150GB | 20GB | ~4-5 saat |
| `whisper_stage2_h100.json` | `stage2` | H100 80GB | 150GB | 50GB | ~2 saat |
| `qwen_4090.json` | `qwen` | RTX 4090 | 120GB | 20GB | ~7 saat |
| `ollama_inference.json` | `ollama` | RTX 4090 | 30GB | — | stateless |

## ISSAI Dataset — Kritik Notlar

### Tar extraction
- `ISSAI_TSC_218.tar.gz` **21.4GB**, içinde **186K utterance** (tümü tek tar'da)
- HF dataset viewer bozuk ama veri eksiksiz: `https://huggingface.co/datasets/issai/Turkish_Speech_Corpus`
- Extraction ~15-20 dakika sürer (H100 pod, NFS volume)
- **`set -e` + `tar -xzf` = ÖLÜMCÜL**: tar, chown izin hatası verince exit code ≠ 0 → set -e scripti öldürür, extraction yarıda kalır
- **Doğru komut — `/root/` (container SSD) kullan, volume NFS'e yazma:**
  ```bash
  # NFS volume (/workspace) çok yavaş: 1K WAV/dakika
  # Container SSD (/root, 150GB) 60× daha hızlı: 65K WAV/dakika
  mkdir -p /root/issai/extracted
  nohup tar --no-same-owner -xzf /workspace/issai/ISSAI_TSC_218.tar.gz \
    -C /root/issai/extracted/ 2>/dev/null > /workspace/extract.log 2>&1 &
  # ~2 dakika sürer (container SSD), ~167 dakika sürer (NFS volume)
  ```
- Extraction bittikten sonra WAV sayısını doğrula: `find /root/issai/extracted -name "*.wav" | wc -l` → ~164K bekleniyor (Train split)
- `stage2.sh` otomatik `/root/issai/extracted` → `/workspace/issai/extracted` → indir sırasını dener (container SSD önce)

### Disk yönetimi (50GB volume)
| Dosya | Boyut |
|---|---|
| `ISSAI_TSC_218.tar.gz` | 21GB |
| `extracted/` (186K WAV+TXT) | ~25GB |
| `issai_punctuated.jsonl` | 26MB |
| Training checkpoints | ~6GB |
| **Toplam** | ~52GB → tar'ı extraction sonrası sil |

Tar extraction tamamlanınca tar.gz'yi sil (Python ile):
```python
import os; os.remove("/workspace/issai/ISSAI_TSC_218.tar.gz")
```

### ISSAI yapısı
- Format: `Train/XXXXXX.wav` + `Train/XXXXXX.txt` (flat, speaker subdirectory yok)
- WAV: 16kHz mono, ortalama ~5 saniye
- TXT: tek satır, lowercase, noktalama yok, sonu `---` ile bitebilir
- Stage 2'de `issai_gt_punctuated.jsonl` lookup ile TXT → noktalı metin eşleştirmesi
- **Bu dosyayı Mac'te üretme** — pod üzerinde Qwen 7B ile üret (daha kaliteli, özel isimler dahil)

## Notlar

- SECURE cloud zorunlu — COMMUNITY'de Docker Hub/HF download timeout riski
- Pod **silinse de** volume (/workspace) korunur
- SSH public key: `~/.ssh/id_ed25519.pub` içeriği → `SSH_PUBLIC_KEY` env var
- `HF_TOKEN` olmadan HF download çok yavaş (rate limit)
