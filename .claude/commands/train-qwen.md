# Qwen Adapter Training

Yeni bir Qwen LoRA adapter eğit. Mevcut versiyon: `ml/qwen/CHANGELOG.md`.

## ⚠️ KRİTİK KURALLAR — ÖNCE OKU

1. **Mac mlx_lm.lora KULLANMA** — `num_layers=16` (28 olmalı) + `scale=20.0` (2.0 olmalı) → adapter base model'den kötü, input'u aynen geri döndürür. v4 tam bu yüzden silindi.
2. **unsloth KULLANMA** — torch version hell, RunPod'da kurulmuyor.
3. **torchvision KALDIR** — `pip uninstall -y torchvision` yoksa `torchvision::nms` hatası çıkar.
4. **Stack kesin:** `transformers==4.47.0` + `peft==0.13.0` + `trl==0.13.0` — başka versiyon deneme.
5. **torch 2.11.0+cu130 KULLANMA** — CUDA 12.4 ile uyumsuz. `torch==2.5.1` + cu124 index.
6. **SECURE cloud** — RunPod Community'de Docker Hub timeout olur. Sadece SECURE cloud pod'u aç.
7. **Val loss yetmez** — eğitim bitince mutlaka gerçek örneklerle test et (input passthrough kontrolü).
8. **Dataset format**: Qwen chat template — `{"messages": [{"role": "user", ...}, {"role": "assistant", ...}]}`. `input`/`output` field'ı değil.
9. **7B minimum** — 1.5B/3B Türkçe'de hallüsinasyon yapıyor.

---

## ADIM 1 — Dataset Hazırla (Mac local)

### Mevcut data nerede?
```
ml/qwen/data/          ← ham jsonl çiftler
ml/qwen/datasets/v3/   ← birleştirilmiş train/valid (gitignore)
ml/qwen/generators/    ← üretici scriptler (API yok, hardcoded)
```

### Yeni veri üret (gerekirse):
```bash
cd /path/to/voiceflow

# Filler data (mevcut, yeniden üretmek gerekmez)
python ml/qwen/generators/gen_filler_initial.py    # 387 pair
python ml/qwen/generators/gen_filler_complex.py    # 167 pair
python ml/qwen/generators/gen_filler_semantic.py   # 400 pair
python ml/qwen/generators/gen_filler_backtrack.py  # 105 pair

# Ofis konuşmaları (mail, chat, toplantı)
python ml/qwen/generators/gen_office_data.py       # ~158 pair
```

### Dataset build:
```bash
# v3 (2155 pair — aktif)
python ml/qwen/scripts/build_v3_dataset.py

# v4 (3096 pair — filler + persona + office)
python ml/qwen/scripts/build_v4_dataset.py

# Çıktı: ml/qwen/datasets/vN/train.jsonl + valid.jsonl
```

### Dataset doğrula:
```bash
python -c "
import json
with open('ml/qwen/datasets/v4/train.jsonl') as f:
    lines = [json.loads(l) for l in f]
print(f'Train: {len(lines)} pair')
# Format kontrolü
sample = lines[0]
assert 'messages' in sample, 'YANLIŞ FORMAT! messages field yok'
assert sample['messages'][0]['role'] == 'user', 'İlk role user olmalı'
print('Format OK')
print('Örnek:', sample['messages'][0]['content'][:80])
"
```

---

## ADIM 2 — RunPod Pod Aç

**Zorunlu config:**
- GPU: H100 SXM (tercih) veya A100 80GB
- Cloud: **SECURE** (Community değil)
- Image: `runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04`
- Disk: Volume 20GB + Container 50GB

```bash
cd runpod && python create_pod.py qwen
# Ya da manual: RunPod UI → SECURE cloud → H100
```

Pod açılınca IP ve PORT al.

---

## ADIM 3 — Dosyaları Pod'a Yükle

```bash
POD_IP="<IP>"
POD_PORT="<PORT>"
VERSION="v4"

# Dataset
scp -P $POD_PORT ml/qwen/datasets/$VERSION/train.jsonl root@$POD_IP:/workspace/train.jsonl
scp -P $POD_PORT ml/qwen/datasets/$VERSION/valid.jsonl root@$POD_IP:/workspace/valid.jsonl

# Training script
scp -P $POD_PORT ml/qwen/scripts/train_hf.py root@$POD_IP:/workspace/train_hf.py
```

---

## ADIM 4 — RunPod'da Bağımlılık Kur

```bash
ssh -p $POD_PORT root@$POD_IP

# Torch — cu124 index zorunlu
pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu124

# torchvision KALDIR (nms hatası çıkar)
pip uninstall -y torchvision

# Stack — bu versiyonları değiştirme
pip install transformers==4.47.0 peft==0.13.0 trl==0.13.0 accelerate datasets

# Doğrula
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
python -c "import transformers; print(transformers.__version__)"
```

---

## ADIM 5 — Eğitim Başlat

```bash
# train_hf.py içindeki config (değiştirme):
# BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
# batch=4, grad_accum=4, LR=5e-6, MAX_STEPS=800
# rank=8, alpha=16 → scale=2.0 (DOĞRU)
# target_modules: tüm 28 layer (DOĞRU)

# HF token ile başlat (model indirme hızlanır)
HF_TOKEN=<token> nohup python /workspace/train_hf.py > /workspace/training.log 2>&1 &

# Logları takip et
tail -f /workspace/training.log
```

### Beklenen çıktı:
```
Step 100/800: loss=0.8x
Step 400/800: loss=0.6x
Step 800/800: eval_loss=0.5x   ← 0.55 altı hedef
```

### GPU util kontrolü (RunPod UI yanıltıcı):
```bash
nvidia-smi  # VRAM%'e bak, UI'daki GPU% render engine ölçer
```

---

## ADIM 6 — Adapter İndir + MLX'e Dönüştür

```bash
# RunPod'dan indir
VERSION_N="4"
scp -rP $POD_PORT root@$POD_IP:/workspace/adapters_v${VERSION_N} \
    ml/qwen/adapters/v${VERSION_N}.0-hf

# MLX'e dönüştür
python ml/qwen/scripts/convert_adapter.py \
    --input ml/qwen/adapters/v${VERSION_N}.0-hf \
    --output ml/qwen/adapters/v${VERSION_N}.0

# Boyut kontrolü (~35-45MB beklenir)
du -sh ml/qwen/adapters/v${VERSION_N}.0/
```

---

## ADIM 7 — KALİTE TESTİ (val_loss yetmez!)

```bash
# Backend'i yeni adapter ile başlat
# config.yaml → llm.adapter_path: ml/qwen/adapters/v4.0

python -c "
# Basit smoke test
test_cases = [
    ('şey bunu yani söylemek istiyorum ki sistem çalışıyor', 'sistem çalışıyor'),
    ('tamam yani ee toplantı yarın saat üçte', 'toplantı yarın saat üçte'),
    ('hani şey pull request açtım', 'pull request açtım'),
]
# Backend üzerinden test et ya da mlx-lm ile direkt
"

# MUTLAKA kontrol et:
# 1. Input passthrough YOK (adapter input'u aynen döndürmüyor)
# 2. Filler siliniyor (yani, şey, hani, ee, işte)
# 3. Anlamsal filler korunuyor ('yani bu doğru değil' → 'yani' kalmalı)
# 4. Noktalama düzeltiliyor
# 5. Türkçe karakter düzeltiliyor (i→İ, s→ş vs)
```

### Input passthrough test (KRİTİK):
```bash
# Bu çıktı input'a birebir eşitse adapter BOZUK
echo "şey bunu yani kontrol et" | python -c "
from mlx_lm import load, generate
model, tokenizer = load('mlx-community/Qwen2.5-7B-Instruct-4bit',
    adapter_path='ml/qwen/adapters/v4.0')
# test
"
```

---

## ADIM 8 — Aktifleştir

Testler geçtiyse:

```yaml
# config.yaml
llm:
  adapter_path: ml/qwen/adapters/v4.0
  adapter_version: "4.0"
  adapter_trained_at: "YYYY-MM-DD"
```

### CHANGELOG güncelle (`ml/qwen/CHANGELOG.md`):
```markdown
## v4.0 — YYYY-MM-DD ✅ AKTİF

**Dosya:** `adapters/v4.0/` | **HF:** `tkosen/voiceflow-qwen-adapter-v4`

- [Ne öğretti, ne ekledi]
- [Hangi hataları düzeltti]

**Eğitim:** RunPod H100, 800 step, eval_loss: X.XXX
**Dataset:** XXXX pair (...)
```

---

## HATA KATALOĞU

| Hata | Sebep | Çözüm |
|------|-------|-------|
| `torchvision::nms` | torchvision yüklü | `pip uninstall -y torchvision` |
| `ImportError: cannot import 'Trainer'` | transformers 5.x + peft circular import | `pip install transformers==4.47.0` |
| `trl requires transformers>=5.x` | trl 1.0.0 | `pip install trl==0.13.0` |
| CUDA error / OOM | torch 2.11+cu130 ile H100 uyumsuz | `torch==2.5.1 --index-url .../cu124` |
| Adapter val_loss düşük ama kötü | mlx_lm.lora default'ları kırık | RunPod HF training kullan, Mac değil |
| Input passthrough | `num_layers=16`, `scale=20.0` | train_hf.py ile yeniden eğit (28 layer, scale=2.0) |
| Train loss NaN (resume) | MLX adapter resume sırasında bozulma | Resume olmadan yeniden başlat |
| Docker Hub timeout | Community cloud | SECURE cloud pod'u kullan |
| Model indirme yavaş | HF_TOKEN yok | `HF_TOKEN=xxx` export et |
| KeyError: tech_rate | Eski overnight_train.py profili | overnight_train.py güncel versiyonu kullan |

---

## REFERANS

- Aktif adapter: `config.yaml → llm.adapter_path`
- Versiyon geçmişi: `ml/qwen/CHANGELOG.md`
- Training script: `ml/qwen/scripts/train_hf.py`
- Convert script: `ml/qwen/scripts/convert_adapter.py`
- RunPod configs: `runpod/pods/`, `runpod/setup/`
- Detay: `docs/ml/runpod-finetuning.md`
