# Türkçe NLP Datasetleri — HuggingFace Araştırması

**Tarih:** 2026-04-01
**Amaç:** VoiceFlow LoRA adapter fine-tuning için Türkçe dataset kaynakları

---

## Metin Düzeltme / Gramer

| Dataset | Açıklama | Boyut | Güncelleme |
|---|---|---|---|
| **GECTurk** | Türkçe dilbilgisi hata düzeltme. 20+ kural, 130K paralel cümle, gerçek film yorumlarıyla test seti. Seq2seq baseline mevcut. | 130K cümle | Sep 2023 |
| **NoisyWikiTr** | Ham Türkçe Wikipedia + gürültü → yazım düzeltme dataseti | ~milyonlarca satır | 2024 |
| **TrGLUE — TrCOLA** | Türkçe dilbilgisi kabul edilebilirlik sınıflaması | 9.92K | Dec 2025 |
| **Ba2han/TDK_Sozluk-Turkish** | TDK sözlük — yazım ve anlam doğrulama referansı | 133K | Sep 2024 |

**VoiceFlow için öncelik:** GECTurk — doğrudan (bozuk → düzgün) formatında, LoRA training'e hazır.

---

## ASR / STT

| Dataset | Açıklama | Boyut | Güncelleme |
|---|---|---|---|
| **issai/Turkish_Speech_Corpus** | En büyük açık kaynak Türkçe konuşma dataseti. MIT lisanslı. | 218.2 saat / 186K utterance | 2023 |
| **ysdede/khanacademy-turkish** | Khan Academy YouTube, VAD + forced alignment. Temiz STEM Türkçesi. 16kHz. | 78 saat / 27.1K örnek | 2024 |
| **emre/Open_SLR108_Turkish_10_hours** | MediaSpeech YouTube, manuel transkripsiyon | 10 saat | 2023 |
| **cubukcum/TurkishVoiceDataset** | Geniş ASR dataseti | 29.6 GB | 2025 |
| **Appenlimited/700h-tr-turkish-text-to-speech** | Türkçe TTS — STT için ters kullanılabilir | 700 saat | 2023-2024 |
| **google/fleurs (tr)** | Çok dilli ASR benchmark, Türkçe alt kümesi | 3.1K kayıt | Aktif |

**VoiceFlow için öncelik:** issai/Turkish_Speech_Corpus — Whisper hata pattern'leri çıkarmak için, gerçek ses + transkripsiyon pair'leri.

---

## Paraphrase / Cümle Yapısı

| Dataset | Açıklama | Boyut | Güncelleme |
|---|---|---|---|
| **TrGLUE — TrQQP** | Türkçe soru çiftleri parafraz tespiti | 369K | Dec 2025 |
| **TrGLUE — TrMRPC** | Haber kaynaklı cümle çiftleri, semantik eşdeğerlik | 5.18K | Dec 2025 |
| **TrGLUE — TrSTS-B** | Semantik benzerlik skoru (1-5) | 3.36K | Dec 2025 |
| **synturk/turkish-sentence-elements** | Cümle ögesi etiketleme (özne/nesne/yüklem) | — | 2024 |
| **community-datasets/tapaco** | Tatoeba Paraphrase Corpus — çok dilli | 1.9M toplam | Aktif |

**VoiceFlow için öncelik:** synturk/turkish-sentence-elements — SOV kelime sırası düzeltme için.

---

## Öncelikli Aksiyon

1. **GECTurk** indir → `prepare_dataset.py`'a ekle → tekrar fine-tune
2. **synturk/turkish-sentence-elements** → kelime sırası düzeltme örnekleri çıkar
3. **issai/Turkish_Speech_Corpus** → Whisper ile çalıştırıp gerçek hata pair'leri üret (`whisper_loop.py` benzeri)

---

## Kaynaklar

- https://huggingface.co/datasets/turkish-nlp-suite/TrGLUE
- https://huggingface.co/papers/2309.11346 (GECTurk)
- https://huggingface.co/datasets/issai/Turkish_Speech_Corpus
- https://huggingface.co/datasets/ysdede/khanacademy-turkish
- https://huggingface.co/datasets/synturk/turkish-sentence-elements
- https://github.com/GGLAB-KU/gecturk
