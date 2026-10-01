# CoreML / WhisperKit — Neden Elendi

**Tarih:** 2026-09-30 · **Karar:** MLX + Python'da kalındı · **Ölçüm donanımı:** M4, 16 GB

## Özet

Mac uygulamasını paketlenebilir hale getirmek için çıkarımı Python/MLX'ten Swift'e
(WhisperKit + CoreML) taşımayı değerlendirdik. **Taşıma gerekçesiz bulundu:** kısa
diktede 2.5 kat yavaş, aynı boyut, üstüne 15 dakikalık ilk yükleme.

Bu notun amacı: aynı soru tekrar geldiğinde baştan ölçülmesin.

---

## Ölçümler

Dört gerçek dikte kaydı (`ml/whisper/datasets/user_corrections/pending/`), aynı model
(`v2.0` fine-tune), aynı makine. Her iki motor da ikişer kez çalıştırıldı, en iyi süre alındı.

| Ses | MLX dinamik pencere | MLX sabit 30sn | WhisperKit (CoreML) |
|---|---|---|---|
| 3.2 sn | **311 ms** | 3034 ms | 765 ms |
| 11.9 sn | **814 ms** | 1686 ms | 1011 ms |
| 27.6 sn | **2092 ms** | 2314 ms | 2872 ms |
| 35.0 sn | 3320 ms | 4330 ms | **3191 ms** |

WhisperKit dört klipten üçünde daha yavaş. Yalnızca 35 saniyelik uzun kayıtta %4 öne
geçiyor — ve uzun kayıt tipik kullanım değil.

### Boyut

| Bileşen | Boyut |
|---|---|
| AudioEncoder.mlmodelc | 1.2 GB |
| TextDecoder.mlmodelc | 328 MB |
| MelSpectrogram.mlmodelc | 392 KB |
| **Toplam (fp16)** | **1.5 GB** |

MLX modeliyle aynı. WhisperKit README'sindeki **626 MB** rakamı Argmax'ın *kuantize*
varyantı içindir, fp16 dönüşüm için geçerli değildir. Bu rakam yanlış okunduğu için
taşıma başta cazip göründü — asıl hata buydu.

### İlk yükleme

**933 saniye (15.5 dakika).** CoreML, 1.2 GB'lık encoder'ı ilk açılışta ANE için
derliyor. Bir kez oluyor, sonrası önbellekli — ama son kullanıcının ilk açılışında
yaşanır. Kabul edilebilir olması için arka planda, ilerleme göstergeli bir hazırlık
akışı gerekir.

---

## Kök sebep: dinamik pencere taşınamıyor

MLX'teki hız avantajı `transcription/dynamic_window.py`'den geliyor: encoder penceresi
ses uzunluğuna göre kısaltılıyor (3.2 sn ses → 7 sn pencere). CoreML modellerinde girdi
şekli **derleme anında sabitlenir**; 30 saniyelik pencere modele gömülür.

`whisperkit-generate-model` CLI'ında encoder penceresi için seçenek yok
(`--text-decoder-max-sequence-length` decoder tarafıdır, işe yaramaz). Kısa pencereli
bir CoreML varyantı üretmek whisperkittools'un model tanımını yamalamayı gerektirir.

Pratik sonuç: **ANE avantajı, dinamik pencere avantajını kapatmıyor.**

---

## Dönüşüm doğruluğu: test güvenilmez, çıktı iyi

### Argmax'ın doğruluk testi bizim checkpoint'te savruluyor

`torch2torch` testi (PyTorch ↔ PyTorch, CoreML devrede değil) aynı model ve aynı config
ile tekrarlandığında:

```
PSNR:   9.32 · 12.6 · 16.8 · 138        ← bizim v2.0
PSNR:   133 (kararlı)                   ← openai/whisper-large-v3-turbo
argmax: %0 ve %100 arasında gidip geliyor
```

İki dizin birebir aynı içerikteyken biri %100 diğeri %0 verdi. Test rastgele girdi
kullanıyor; fine-tune edilmiş modelde üst iki logit yakın olduğunda argmax karşılaştırması
yazı-tura oluyor.

**Sonuç: bu testin verdiği PSNR/argmax sayılarına bakarak karar vermeyin.** Ampirik
transkripsiyon karşılaştırması yapın.

### Ampirik doğruluk korunuyor

```
MLX        : Ben Kanvasta böyle görüyorum, ama gerçekte.
WhisperKit : Ben kanvasta böyle görüyorum, ama gerçekte.

MLX        : Anladım, bu kadromu kırda henüz taraftar data ol…
WhisperKit : Anladım, bu kadro mu kırda henüz taraftar data ol…
```

Türkçe çıktı pratik olarak aynı — büyük harf ve kelime ayırma dışında fark yok.
**Fine-tune'umuz CoreML'e sağlam geçiyor.** iOS'a geçilirse bu yol açıktır.

---

## Tekrar denemek isteyen için

```bash
python3.11 -m venv .venv && ./.venv/bin/pip install git+https://github.com/argmaxinc/whisperkittools.git
./.venv/bin/whisperkit-generate-model --model-version tkosen/voiceflow-whisper-tr-v2 --output-dir out
```

Bilinmesi gerekenler:

- **Dönüşüm testlerin İÇİNDE yapılır.** `--disable-default-tests` verirseniz model de
  üretilmez; yalnızca MelSpectrogram çıkar. Decoder testi kalırsa `TextDecoder.mlmodelc`
  hiç oluşmaz — testin geçtiği turu yakalayana kadar tekrar çalıştırın.
- Dönüşüm ~25 dk (encoder ağır kısım), ara dosyalarla birlikte ~2.7 GB disk ister.
- Swift tarafı: `argmaxinc/argmax-oss-swift`, ürün adı `WhisperKit`,
  `WhisperKitConfig(modelFolder:verbose:logLevel:)` ile yerel klasörden yüklenir.

---

## Hangi koşullarda yeniden bakılır

Bu karar şu durumlarda yeniden değerlendirilmeli:

1. **iOS'a geçilirse** — orada MLX yok, CoreML tek seçenek ve dönüşümün çalıştığını
   biliyoruz.
2. **Kuantizasyon denenirse** — `--allowed-nbits 4` boyutu ~600 MB'a indirebilir ve ilk
   yükleme süresini kısaltabilir. Hız zaten yetersizken doğruluktan vermek mantıklı
   görünmediği için denenmedi.
3. **whisperkittools encoder penceresi seçeneği eklerse** — dinamik pencere taşınabilir
   hale gelirse denklem tamamen değişir.

## Python'dan kurtulmak hâlâ gerekiyorsa

Paketleme sorununun kaynağı 1.5 GB'lık model değil, **1.8 GB'lık `backend/.venv`**.
İki yol kaldı:

- **MLX Swift** — MLX'te şekiller dinamik, yani dinamik pencere korunabilir. Swift'te
  Whisper implementasyonu olup olmadığı doğrulanmadı.
- **Python'u paketle** (py2app/PyInstaller + imzalama) — acı verici ama bilinen bir acı;
  hız ve dinamik pencere aynen korunur.

Ölçümlere göre ikincisi daha düşük riskli.
