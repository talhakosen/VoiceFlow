# Qwen Adapter Changelog

Aktif adapter → `config.yaml: llm.adapter_path`

---

## v3.0 — 2026-04-04 ✅ AKTİF

**Dosya:** `adapters/v3.0/` | **HF:** `tkosen/voiceflow-qwen-adapter-v3`

- Filler temizleme: cümle başı (Yani,/Şey,/Hani,/Tamam,/İşte,), zincirleme, anlamsal ayrım
- Backtrack: "hayır şunu" → son niyet
- Noktalama + Türkçe karakter + büyük harf

**Eğitim:** RunPod H100, 800 step, 11 dk, eval_loss: **0.513**
**Dataset:** 2155 pair (filler_initial 387 + complex 167 + semantic 400 + backtrack 105 + v2 1096)

---

## v2.0 — 2026-04-04

- Filler (şey/yani/hani/işte/ee), backtrack, stutter, sayı normalizasyonu
- RunPod H100, 400 step, 3 dk, eval_loss: 0.71
- Dataset: 1096 pair

## v1.0 — 2026-04-02

- Noktalama, Türkçe karakter, temel filler
- RTX 4090, 7 saat, unsloth, dataset: 71K pair (GECTurk)

---

## ❌ v4.0 — BAŞARISIZ (Mac mlx_lm.lora)

Mac M4'te `mlx_lm.lora` ile eğitildi. Val loss 0.428 görünüyor ama **gerçek testte base model'den kötü** — input'u aynen geri döndürüyor. Sebep: `num_layers=16` (28 değil) + `scale=20.0` (2.0 değil). **Kullanma.**

v4.1–v4.10 overnight round'lar da aynı sorunlu. Tümü silindi.
