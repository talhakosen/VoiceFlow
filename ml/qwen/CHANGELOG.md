# Qwen Adapter Changelog

Aktif adapter → `config.yaml: llm.adapter_path`
Adapter dosyaları gitignore'da — HuggingFace'te yedekli.

---

## v2.0 — 2026-04-04 ✅ AKTİF

**Dosya:** `adapters/v2.0/`
**HF:** `tkosen/voiceflow-qwen-adapter-v2`

**Ne öğrendi:**
- Filler temizleme: şey, yani (gereksiz), hani, işte, ee, aa → sil
- Anlamsal yani (cümle içi bağlaç) → koru
- Backtrack: "hayır şunu demek istiyorum X" → X
- Stutter: "b-b-ben" → "ben"
- Sayı normalizasyonu: "iki yüz elli bin" → "250.000"
- Noktalama + Türkçe karakter (v1'den devralındı)

**Eğitim:**
- Dataset: `datasets/v2/` — 1096 pair (496 filler + 600 v1 mevcut)
- Script: `scripts/train_hf.py`
- GPU: H100 80GB, RunPod SECURE, ~3 dakika
- LR: 8e-6, Steps: 400, eval_loss: 0.71

---

## v1.0 — 2026-04-02

**HF:** `tkosen/voiceflow-qwen-adapter` (arşiv)

**Ne öğrendi:**
- Noktalama ekleme
- Türkçe karakter düzeltme (ASCII → ş/ç/ğ/ı/ö/ü)
- Backtracking düzeltme
- Temel filler temizleme

**Eğitim:**
- Dataset: `datasets/v1/` — 71.437 pair (GECTurk 68K + corruption 3K)
- Script: `scripts/train_runpod.py`
- GPU: RTX 4090, ~7 saat, unsloth SFTTrainer

---

## Yeni versiyon eğitmek için

```bash
# 1. Dataset hazırla
python scripts/prepare_dataset_v2.py   # veya yeni prepare_dataset_vN.py

# 2. RunPod H100 aç
cd runpod && python create_pod.py qwen

# 3. Dataset + script yükle
scp -P <PORT> datasets/vN/train.jsonl root@<IP>:/workspace/train_v2.jsonl
scp -P <PORT> datasets/vN/valid.jsonl root@<IP>:/workspace/valid_v2.jsonl
scp -P <PORT> scripts/train_hf.py root@<IP>:/workspace/

# 4. Deps + training
ssh -p <PORT> root@<IP> "pip install -q transformers==4.47.0 peft==0.13.0 trl==0.13.0 accelerate datasets"
ssh -p <PORT> root@<IP> "nohup python /workspace/train_hf.py > /workspace/training.log 2>&1 &"

# 5. İndir + dönüştür
scp -rP <PORT> root@<IP>:/workspace/adapters_v2 ./adapters/vN.0-hf
python scripts/convert_adapter.py  # → adapters/vN.0/

# 6. config.yaml güncelle + CHANGELOG'a ekle
```
