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

```bash
# 1. Pod oluştur (RTX 4090 yeterli — ~30 dk)
python create_pod.py qwen

# 2. Dataset + script + V1 adapter yükle
scp -rP <PORT> ../ml/qwen/adapters_mlx/raw root@<IP>:/workspace/adapters_v1   # V1'den devam
scp -P <PORT> ../ml/qwen/datasets/v2/train.jsonl root@<IP>:/workspace/train_v2.jsonl
scp -P <PORT> ../ml/qwen/datasets/v2/valid.jsonl root@<IP>:/workspace/valid_v2.jsonl
scp -P <PORT> ../ml/qwen/scripts/train_runpod_v2.py root@<IP>:/workspace/
scp -P <PORT> setup/qwen.sh root@<IP>:/workspace/

# 3. SSH + setup + training
ssh -p <PORT> root@<IP>
bash /workspace/qwen.sh          # unsloth kurulum (~15 dk)
python /workspace/train_runpod_v2.py   # training (~30 dk 4090, ~15 dk H100)

# 4. Adapter indir + MLX'e dönüştür
scp -rP <PORT> root@<IP>:/workspace/adapters_v2 ../ml/qwen/adapters_v2_runpod
cd ../ml/qwen/scripts && python convert_adapter.py \
  --input ../adapters_v2_runpod --output ../adapters_v2_mlx

# 5. config.yaml güncelle
# llm:
#   adapter_path: ml/qwen/adapters_v2_mlx
```

**Training config:** LR=8e-6 (catastrophic forgetting önlemi), MAX_STEPS=500, bf16, adamw_8bit.

**Bilinen sorun — unsloth + bitsandbytes:**
RTX 4090 (CUDA 12.x) → `bitsandbytes` sorun çıkarırsa `optim="adamw_torch"` kullan.

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
