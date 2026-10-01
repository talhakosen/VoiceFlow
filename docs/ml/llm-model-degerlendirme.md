# Correction LLM Değerlendirmesi — Qwen3-4B seçildi (2026-10-01)

Local MLX corrector `Qwen2.5-7B + v3.0 adapter` → **`Qwen3-4B-Instruct-2507-4bit`, adapter'sız**.
Config: `config.yaml → llm.mlx_model`.

## Eval — v3 test seti (106 held-out çift, production `MLXCorrector` yolu)

| | Düzeltmesiz | **Qwen3-4B** | Qwen2.5-7B + v3.0 |
|---|---|---|---|
| WER (küçük harf) | 0.490 | **0.321** | 0.396 |
| WER — çözülebilir 91 vaka | 0.430 | **0.283** | 0.358 |
| Exact match | — | **29/106** | 18/106 |
| İçerik uydurma | — | 1 | 3 |
| Süre ort / p90 (M4, prompt cache) | — | **1001 / 1595 ms** | 1691 / 2845 ms |
| Bellek (tepe) | — | **~2.8 GB** | ~4.5 GB |

15 vakanın referansı gerçek ses transkriptinden geliyor, girdide olmayan kelimeler içeriyor
(çözülemez) — ayrı ölçüldü, sıralama değişmedi.

## Elenenler (7 cümlelik hızlı test, prompt cache açık)

- **Qwen3-8B** (hibrit, `enable_thinking=False` gerekir): 1736 ms, 5.1 GB — 4B'den iyi değil
  (`ondört` → `on on dört`, gereksiz tırnak). 2x yavaşlığa değmez.
- **Ministral-8B-2410**: İngilizce yanıt verdi, sistem prompt'taki örnekleri döktü, özel isim
  büyütmedi. Tokenizer regex uyarısı vardı ama bu davranışı açıklamaz.
- **Kumru-2B**: Düzeltmek yerine soruyu yanıtladı, içerik uydurdu.

## Bilinen zayıflıklar → v4 adapter (Qwen3-4B tabanlı) eğitilirse

- Dolgu temizliği zayıf: `Ee, işte, yani, hani, şey, …` → sadece `Ee` siliniyor (v3.0'ın işiydi).
- Nadiren kelime değiştiriyor: `şu` → `Bu`, `dokümante edildi mi` → `dokümantasyonu yapıldı mı`.
- Kesme işareti: `pipeline ı` → `pipelineı`.

"7B minimum" kuralı Qwen2.5 içindi; Qwen3'te 4B Türkçe'de yeterli (Qwen3 119 dil destekliyor).
