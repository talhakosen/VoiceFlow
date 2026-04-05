# Qwen ASR Correction — Fine-Tuning

Qwen2.5-7B-Instruct LoRA adapter — Whisper çıktısını düzeltir (filler, noktalama, büyük harf).

## Aktif Adapter

`config.yaml` → `llm.adapter_path` — versiyon geçmişi: `CHANGELOG.md`

## Klasör Yapısı

```
ml/qwen/
├── adapters/v3.0/          ← Aktif MLX adapter (RunPod H100)
├── datasets/v1..v4/        ← Eğitim verileri (gitignore)
├── data/*.jsonl             ← Ham çiftler (filler, persona, office)
├── generators/              ← Veri üretici scriptler (API yok, hardcoded)
├── scripts/
│   ├── train_hf.py          ← RunPod eğitim (transformers + peft + trl)
│   ├── convert_adapter.py   ← HF PEFT → MLX dönüşümü
│   ├── build_v3_dataset.py  ← v3 dataset birleştirici
│   ├── build_v4_dataset.py  ← v4 dataset birleştirici
│   └── overnight_train.py   ← Mac local döngüsel eğitim
└── CHANGELOG.md             ← Tüm versiyonlar + eğitim detayları
```

## Eğitim (RunPod H100 — ÖNERİLEN)

```bash
# 1. Pod aç
cd runpod && python create_pod.py qwen

# 2. Yükle
scp -P <PORT> datasets/vN/train.jsonl root@<IP>:/workspace/
scp -P <PORT> datasets/vN/valid.jsonl root@<IP>:/workspace/
scp -P <PORT> scripts/train_hf.py root@<IP>:/workspace/

# 3. Deps + eğitim
pip install transformers==4.47.0 peft==0.13.0 trl==0.13.0 accelerate datasets
nohup python /workspace/train_hf.py > training.log 2>&1 &

# 4. İndir + MLX dönüştür
scp -rP <PORT> root@<IP>:/workspace/adapters_vN ./adapters/vN.0-hf
python scripts/convert_adapter.py --input adapters/vN.0-hf --output adapters/vN.0
```

## ⚠️ Kritik Bulgular

**RunPod HF eğitim KULLAN, Mac mlx_lm.lora KULLANMA:**

| | RunPod (HF) | Mac (mlx_lm.lora) |
|---|---|---|
| Layers | 28 (tümü) | 16 (default) |
| Scale | 2.0 (alpha=16, rank=8) | **20.0** (default) |
| Sonuç | Filler siler, noktalama düzeltir | **Base model'den kötü** |

Mac `mlx_lm.lora` default'ları (`num_layers=16`, `scale=20.0`) Qwen 7B'ye zarar veriyor. Adapter eğitimden sonra input'u aynen geri döndürüyor — base model bile daha iyi.

**Stack (doğrulanmış, hata vermez):**
- `transformers==4.47.0` + `peft==0.13.0` + `trl==0.13.0`
- unsloth KULLANMA (torch version hell)
- Image: `runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04`

**7B minimum** — 1.5B/3B Türkçe'de hallüsinasyon yapıyor.
