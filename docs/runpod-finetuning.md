# RunPod — Fine-Tuning Pod Kurulum Rehberi

## Özet

Unsloth + HuggingFace TRL ile Qwen2.5-7B LoRA fine-tuning.
RTX 4090 üzerinde 1 epoch (~113K örnek) = 3-5 saat, ~$2-3.

---

## Pod Oluşturma (Sorunsuz Çalışan Config)

```
Image:          runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04
Cloud:          SECURE (Community'de Docker Hub timeout riski!)
GPU:            NVIDIA GeForce RTX 4090
Container Disk: 50 GB  (model ~15GB + unsloth ~5GB + dataset + output)
Volume:         20 GB → /workspace
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

## Dataset Yükleme

```bash
# Mac'ten pod'a SCP ile yükle
scp -P <TCP_PORT> -i ~/.ssh/id_ed25519 \
  backend/scripts/training/train.jsonl \
  backend/scripts/training/valid.jsonl \
  root@<PUBLIC_IP>:/workspace/
```

---

## Training Script

`backend/scripts/training/train_runpod.py` — unsloth SFTTrainer.

```bash
# Pod'a yükle
scp -P <TCP_PORT> -i ~/.ssh/id_ed25519 \
  backend/scripts/training/train_runpod.py \
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
BATCH_SIZE  = 2
GRAD_ACCUM  = 4   # effective batch = 8
LR          = 1e-5
NUM_EPOCHS  = 1
OUTPUT_DIR  = "/workspace/adapters"
```

- `bf16=True` (RTX 4090 destekler, fp16 değil)
- `use_gradient_checkpointing="unsloth"` (unsloth'un özel implementasyonu)
- Eval + save her 500 adımda

---

## Adapter İndirme (Training Sonrası)

```bash
# Pod'dan Mac'e indir
scp -P <TCP_PORT> -r -i ~/.ssh/id_ed25519 \
  root@<PUBLIC_IP>:/workspace/adapters/ \
  backend/scripts/training/adapters_runpod/
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
    hf_path='scripts/training/adapters_runpod',
    mlx_path='scripts/training/adapters_mlx',
    quantize=False
)
"
```

Sonra `.env`'deki `LLM_ADAPTER_PATH` → `scripts/training/adapters_mlx` yap.

---

## Maliyet

| GPU | Fiyat | 1 epoch (113K) | Tahmini maliyet |
|-----|-------|----------------|-----------------|
| RTX 4090 | $0.59-0.60/hr | 3-5 saat | ~$2-3 |
| A100 40GB | ~$1.89/hr | 1-2 saat | ~$2-4 |

---

## Kritik Notlar

- **SECURE cloud zorunlu** — Community'de Docker Hub bağlantısı timeout olabilir
- **nohup kullan** — bağlantı kesilse training devam eder, `training.log`'a yazar
- **Tokenization süresi** — 113K örnek ~2-3 dakika (64 paralel worker)
- **GPU util** tokenization'da %10, training başlayınca %80-100 olur
- **bf16=True** RTX 4090 için (Ampere+ mimarisi destekler)
- **Flash Attention 2** kurulu olmayabilir — unsloth otomatik Xformers'a geçer, performans farkı minimal
- **Pod durdurma** — training bitince hemen durdur, $0.60/hr boşa gider
