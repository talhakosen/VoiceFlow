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

### Neden Stage 1'den ~2× daha hızlı

| Faktör | Stage 1 | Stage 2 |
|---|---|---|
| Epoch | 3 | 2 |
| Batch | 16 | **32** |
| Workers | 8 | **16** |
| torch.compile | ✗ | **✓ (+20%)** |
| Adam | default | **8-bit** |
| prefetch_factor | ✗ | **4** |
| RAM disk | ✗ | **✓ (I/O kaldırır)** |

**Tahmini süre: ~2 saat, ~$8 @ H100**

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

# 2. Dosyaları yükle (pod IP/PORT RunPod UI'dan)
scp -P <PORT> ../ml/whisper/whisper_stage2_finetune.py root@<IP>:/workspace/
scp -P <PORT> ../ml/whisper/datasets/issai/issai_punctuated.jsonl root@<IP>:/workspace/
scp -P <PORT> setup/stage2.sh root@<IP>:/workspace/

# 3. SSH + setup + train (her şeyi otomatik yapar)
ssh -p <PORT> root@<IP> 'export HF_TOKEN=hf_xxx && bash /workspace/stage2.sh'

# 4. Log takip
ssh -p <PORT> root@<IP> 'tail -f /workspace/stage2.log'

# 5. Bittikten sonra model indir
scp -rP <PORT> root@<IP>:/workspace/voiceflow-whisper-tr-v2 ../ml/whisper/models/
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

## Workflow: Qwen Training

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
- Stage 2'de `issai_punctuated.jsonl` lookup ile TXT → noktalı metin eşleştirmesi

## Notlar

- SECURE cloud zorunlu — COMMUNITY'de Docker Hub/HF download timeout riski
- Pod **silinse de** volume (/workspace) korunur
- SSH public key: `~/.ssh/id_ed25519.pub` içeriği → `SSH_PUBLIC_KEY` env var
- `HF_TOKEN` olmadan HF download çok yavaş (rate limit)
