# RunPod — Fine-Tuning Pod Kurulum Rehberi

## Özet

Unsloth + HuggingFace TRL ile Qwen2.5-7B LoRA fine-tuning.
RTX 4090 üzerinde 1 epoch (~305K örnek) = ~8-10 saat, ~$5-6.

---

## Pod Oluşturma (Sorunsuz Çalışan Config)

```
Image:          runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04
Cloud:          SECURE (Community'de Docker Hub timeout riski!)
GPU:            NVIDIA GeForce RTX 4090
Container Disk: 120 GB (model ~15GB + unsloth ~5GB + dataset ~50GB + output)
Volume:         20 GB → /workspace  ← SADECE çıktı dosyaları buraya yaz!
Ports:          22/tcp, 8888/http
Env:            PUBLIC_KEY = <ssh public key>
```

**SSH key:** `~/.ssh/id_ed25519` (ed25519, RunPod'a kayıtlı)

---

## Bağlantı

```bash
# Direct TCP (SCP/SFTP destekler — dosya transferi için bunu kullan)
ssh root@<PUBLIC_IP> -p <TCP_PORT> -i ~/.ssh/id_ed25519

# Proxy (sadece terminal)
ssh <POD_ID>-<HASH>@ssh.runpod.io -i ~/.ssh/id_ed25519
```

**Önemli:** SCP ile dosya transferi için Direct TCP bağlantısını kullan.

---

## Kurulum (Pod terminali)

```bash
# Bağımlılıkları kur (torch zaten kurulu, sadece bunlar lazım)
pip install unsloth trl datasets -q

# torchaudio uyumsuzluk uyarısı alınabilir — ignore et, kullanmıyoruz
```

---

## Dataset

### Mevcut Dataset (2. Round — Nisan 2026)

| Kaynak | Dosya | Pair |
|---|---|---|
| Sentetik corruption | `qwen/data/corruption_pairs.jsonl` | ~3K |
| ASR training data | `qwen/data/asr_training_data.jsonl` | ~5K |
| Word order | `qwen/data/word_order_pairs.jsonl` | ~2K |
| GecTurk (gerçek metin hataları) | `qwen/data/gecturk_pairs.jsonl` | ~138K |
| ISSAI TSC (gerçek Whisper hataları) | `whisper/datasets/issai/issai_pairs_clean.jsonl` | ~164K |
| **Toplam** | `training/train.jsonl` | **~305K** |

**train: 244K / valid: 30K / test: 30K**

`issai_pairs_clean.jsonl` — ISSAI'den `output_len ≤ input_len * 1.5` filtresi uygulanmış (~13K segment hizalama hatası çıkarıldı).

`prepare_dataset.py` ile üret:
```bash
cd ml/qwen/scripts
python prepare_dataset.py \
  --sources ../../data_gen/datasets/corruption_pairs.jsonl \
            qwen/data/asr_training_data.jsonl \
            qwen/data/word_order_pairs.jsonl \
            qwen/data/gecturk_pairs.jsonl \
            whisper/datasets/issai/issai_pairs_clean.jsonl
```

### Pod'a Yükleme

```bash
# Mac'ten pod'a SCP ile yükle
scp -P <TCP_PORT> -i ~/.ssh/id_ed25519 \
  ml/qwen/datasets/train.jsonl \
  ml/qwen/datasets/valid.jsonl \
  root@<PUBLIC_IP>:/workspace/
```

---

## Training Script

`ml/qwen/scripts/train_runpod.py` — unsloth SFTTrainer.

```bash
# Pod'a yükle
scp -P <TCP_PORT> -i ~/.ssh/id_ed25519 \
  ml/qwen/scripts/train_runpod.py \
  root@<PUBLIC_IP>:/workspace/

# Arka planda başlat (bağlantı kesilse de devam eder)
ssh root@<PUBLIC_IP> -p <TCP_PORT> -i ~/.ssh/id_ed25519 \
  "cd /workspace && nohup python train_runpod.py > training.log 2>&1 &"

# Log takip et
ssh root@<PUBLIC_IP> -p <TCP_PORT> -i ~/.ssh/id_ed25519 \
  "tail -f /workspace/training.log"
```

---

## Training Config (train_runpod.py)

```python
MODEL_NAME  = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
MAX_SEQ_LEN = 512
LORA_RANK   = 8
LORA_ALPHA  = 16
BATCH_SIZE  = 8          # RTX 4090 24GB için optimize (ilk run'da 2'ydi)
GRAD_ACCUM  = 2          # effective batch = 16
LR          = 1e-5
NUM_EPOCHS  = 1
OUTPUT_DIR  = "/workspace/adapters"
```

- `bf16=True` (RTX 4090 destekler, fp16 değil)
- `use_gradient_checkpointing="unsloth"` (unsloth'un özel implementasyonu)
- `optim="adamw_8bit"` — unsloth standart, default AdamW'dan hızlı + VRAM verimli
- `packing=True` — kısa sequence'ları 512 token'a paketler, GPU boş beklemez
- `dataloader_pin_memory=True` — CPU→GPU transfer hızlanır
- Eval + save her 500 adımda

### GPU Utilization Notları

İlk run'da (batch=2, optimizer=default): **GPU %7, CPU %80** — darboğaz.
Neden: batch=2 çok küçük, GPU milisaniyede bitirir, CPU tokenization'ı bekler.
Optimize run (batch=8 + packing + adamw_8bit): **GPU %55-91** — normal training range.

**Eval fazında GPU memory %90+** görünmesi normaldir — valid set inference memory-heavy.
**ISSAI Whisper %40-70 arası dalgalanma** normaldir — ses dosyası uzunluğuna göre değişir.

---

## Adapter İndirme (Training Sonrası)

```bash
# Pod'dan Mac'e indir
scp -P <TCP_PORT> -r -i ~/.ssh/id_ed25519 \
  root@<PUBLIC_IP>:/workspace/adapters/ \
  ml/qwen/adapters_runpod/
```

---

## MLX Formatına Dönüştürme

Unsloth → HuggingFace PEFT formatı çıkarır. Mac app MLX adapter bekler.

```bash
cd backend && source .venv/bin/activate

# HF adapter → MLX formatına dönüştür
python -c "
from mlx_lm import load
from mlx_lm.tuner.utils import convert
convert(
    hf_path='../adapters_runpod',
    mlx_path='../adapters_mlx',
    quantize=False
)
"
```

Sonra `config.yaml`'da `llm.adapter_path: ml/qwen/adapters_mlx` yap.

---

## Maliyet

| GPU | Fiyat | 1 epoch (113K) | Tahmini maliyet |
|-----|-------|----------------|-----------------|
| RTX 4090 | $0.59-0.60/hr | 3-5 saat | ~$2-3 |
| A100 40GB | ~$1.89/hr | 1-2 saat | ~$2-4 |

---

## Disk Kullanımı — Kritik

`/workspace` (volume) ve container disk farklı şeyler:

| Path | Boyut | Ne için |
|------|-------|---------|
| `/` (container disk) | 120GB | İndirme, extract, model, geçici dosyalar |
| `/workspace` (volume) | 20GB | Sadece küçük çıktılar (*.jsonl, adapter/) |

**`df -h` yanıltıcı!** `/workspace` için 257TB gösterir — RunPod network FS'in toplam kapasitesi. Gerçek kota `volumeInGb` parametresi (20GB). 20GB'ı aşan yazma → `Disk quota exceeded`.

**Kural:** Büyük dosyaları (dataset, model) `/root/` veya `/tmp/`'ye indir. Sadece indirmek istediğin çıktıyı `/workspace`'e yaz.

---

## Whisper Stage 2 — H100 Noktalama Fine-Tune

### ISSAI Extraction — Kritik Bilgi

**Tar dosyası:** `ISSAI_TSC_218.tar.gz` — 21.4GB, 186,170 utterance tek tar'da.

**ASLA `/workspace` (NFS)'e extract etme:**
| Path | Hız | 186K WAV için |
|---|---|---|
| `/workspace` (NFS volume) | ~1K WAV/dk | ~167 dakika |
| `/root/` (container SSD) | ~65K WAV/dk | **~3 dakika** |

```bash
# Doğru extraction — container SSD'ye (/root), --no-same-owner zorunlu
mkdir -p /root/issai/extracted
nohup tar --no-same-owner -xzf /workspace/issai/ISSAI_TSC_218.tar.gz \
  -C /root/issai/extracted/ > /workspace/extract.log 2>&1 &

# Doğrula (~3 dk sonra)
find /root/issai/extracted -name "*.wav" | wc -l  # → 186,170 bekleniyor
```

**`set -e` + tar = ÖLÜMCÜL**: tar chown permission hataları exit code ≠ 0 döner → script ölür, extraction ~8K WAV'da durur. `--no-same-owner` ile bu hatalar bastırılır.

### RAM Disk Trick (Training I/O Optimizasyonu)

H100 pod RAM = 200GB+. ISSAI WAV'lar ~26GB → RAM'e kopyala, disk I/O sıfırla → training ~1 saat kısalır.

```bash
free -h  # RAM kontrolü
mkdir -p /dev/shm/issai
cp -r /root/issai/extracted /dev/shm/issai/  # ~60 saniye
# Stage 2 script otomatik: /dev/shm → /root → /workspace sırasını dener
```

### issai_pairs_clean.jsonl Alan Farkı

```json
{"input": "docker kurdum kubernetes e deploy ettim",  ← Whisper ASR çıktısı (Qwen eğitimi için)
 "output": "Docker kurdum, Kubernetes'e deploy ettim."  ← Ground truth TXT (Whisper eğitimi için)
```

**Whisper Stage 2 için:** `output` alanını kullan — TXT dosyasındaki ground truth, `_clean_gt()` ile temel noktalama eklenmiş.
**Qwen için:** `input → output` çifti — Whisper hatalarını düzeltmeyi öğreniyor.

### Stage 2 Optimizasyon (Stage 1 ile karşılaştırma)

| Faktör | Stage 1 | Stage 2 |
|---|---|---|
| Base model | whisper-large-v3-turbo | **voiceflow-whisper-tr** (Stage 1 çıktısı) |
| Epoch | 3 | **2** |
| Batch | 16 | **32** |
| LoRA rank | 16 | **8** (catastrophic forgetting önle) |
| LR | 1e-3 | **5e-6** (200× düşük) |
| Workers | 8 | **16** |
| torch.compile | ✗ | **✓ (+20%)** |
| Adam | default | **adamw_bnb_8bit** |
| prefetch_factor | ✗ | **4** |
| RAM disk | ✗ | **✓** |
| **Süre** | ~4.6 saat | **~2 saat** |
| **Maliyet** | ~$18 | **~$8** |

### Stage 2 Çalıştırma

```bash
python create_pod.py stage2

# 2. Dosyaları yükle
scp -P <PORT> ml/whisper/whisper_stage2_finetune.py root@<IP>:/workspace/
scp -P <PORT> runpod/setup/stage2.sh root@<IP>:/workspace/

# 3. Training başlat
ssh -p <PORT> root@<IP> 'export HF_TOKEN=hf_xxx && bash /workspace/stage2.sh'

# 4. Log takip
ssh -p <PORT> root@<IP> 'tail -f /workspace/stage2.log'
```

---

## ISSAI / Whisper Paralel İşleme

186K ses dosyasını tek process ile işlemek ~26 saat sürer. **3 paralel shard** ile ~9 saate düşer.

### Neden BatchedInferencePipeline değil, paralel process?

`BatchedInferencePipeline(batch_size=16)` **kısa** ses dosyalarında daha **yavaş** çalışır:
- Kısa dosyalar (< 10sn): her dosya zaten 1-2 chunk, batch overhead kazancı yiyor
- Gerçek ölçüm: sequential ~10K dosya/saat, BatchedInferencePipeline ~7K dosya/saat (%30 yavaş)
- Uzun dosyalar (> 30sn) için BatchedInferencePipeline avantajlı

### Paralel shard — RTX 4090 VRAM kapasitesi

`large-v3 float16` = ~3.5GB VRAM. RTX 4090 = 24.5GB.
→ 3 paralel process: 3 × 3.5 = **10.5GB** — rahat sığar, GPU **%99** utilization.

```bash
# 3 shard paralel başlat
SHARD_INDEX=0 SHARD_TOTAL=3 nohup python3 -u process_issai.py > shard0.log 2>&1 &
SHARD_INDEX=1 SHARD_TOTAL=3 nohup python3 -u process_issai.py > shard1.log 2>&1 &
SHARD_INDEX=2 SHARD_TOTAL=3 nohup python3 -u process_issai.py > shard2.log 2>&1 &

# Bitince merge
cat /workspace/issai_pairs_0.jsonl \
    /workspace/issai_pairs_1.jsonl \
    /workspace/issai_pairs_2.jsonl \
    > /workspace/issai_pairs_all.jsonl
```

`process_issai.py` SHARD_INDEX/SHARD_TOTAL env var'ları okur, dosya listesini `sorted()[SHARD_INDEX::SHARD_TOTAL]` ile böler. Her shard kendi `issai_pairs_{N}.jsonl` dosyasına yazar.

---

## Kritik Notlar

- **SECURE cloud zorunlu** — Community'de Docker Hub bağlantısı timeout olabilir
- **nohup kullan** — bağlantı kesilse training devam eder, `training.log`'a yazar
- **Tokenization süresi** — 113K örnek ~2-3 dakika (64 paralel worker)
- **GPU util** tokenization'da %10, training başlayınca %80-100 olur
- **bf16=True** RTX 4090 için (Ampere+ mimarisi destekler)
- **Flash Attention 2** kurulu olmayabilir — unsloth otomatik Xformers'a geçer, performans farkı minimal
- **Pod durdurma** — training bitince hemen durdur, $0.60/hr boşa gider
- **BatchedInferencePipeline kısa dosyalarda yavaş** — ISSAI gibi kısa konuşma parçaları için paralel process daha iyi; uzun dosyalar için BatchedInferencePipeline avantajlı
