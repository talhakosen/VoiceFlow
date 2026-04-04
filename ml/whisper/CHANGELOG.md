# Whisper Model Changelog

Aktif model → `config.yaml: whisper.model`
Model dosyaları gitignore'da — HuggingFace'te yedekli.

---

## v2.0 — 2026-04-04 ✅ AKTİF

**Dosya:** `models/v2.0/`
**HF:** `tkosen/voiceflow-whisper-tr-v2`

**Ne öğrendi:**
- Büyük harf: cümle başları, özel isimler
- Noktalama: nokta, virgül, soru işareti
- v1'in fonetik doğruluğunu korudu

**Eğitim:**
- Base: v1.0 (voiceflow-whisper-tr)
- Dataset: `datasets/issai/` — 164K pair + Qwen 7B fp16 GT noktalama
- Script: `scripts/train_stage2.py`
- GPU: H100 80GB, RunPod SECURE
- Steps: 10.644, Batch: 16 + gradient_checkpointing (32 → OOM)
- Süre: ~2 saat (OOM crash + resume dahil ~4.5 saat)

---

## v1.0 — 2026-04-03

**HF:** `tkosen/voiceflow-whisper-tr` (arşiv, lokalde yok)

**Ne öğrendi:**
- Genel Türkçe fonetik doğruluk
- Lowercase, noktalama yok (ISSAI ground truth böyle)
- v2'nin base'i olarak kullanıldı

**Eğitim:**
- Base: whisper-large-v3-turbo (OpenAI)
- Dataset: `datasets/issai/` — 164K pair
- Script: `scripts/train_stage1.py`
- GPU: H100 80GB, ~4.6 saat, train_loss: 0.186

---

## Yeni versiyon eğitmek için

```bash
# 1. RunPod H100 aç
cd runpod && python create_pod.py stage2

# 2. Script + dataset yükle, training başlat
scp -P <PORT> ml/whisper/scripts/train_stage2.py root@<IP>:/workspace/
ssh -p <PORT> root@<IP> "nohup python /workspace/train_stage2.py > /workspace/training.log 2>&1 &"

# 3. İndir + MLX'e dönüştür
scp -rP <PORT> root@<IP>:/workspace/<output> ./ml/whisper/models/vN.0-hf/
python ml/whisper/scripts/convert_whisper_mlx.py --input models/vN.0-hf --output models/vN.0/

# 4. config.yaml güncelle + CHANGELOG'a ekle
```
