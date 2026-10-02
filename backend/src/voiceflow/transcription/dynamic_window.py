"""Whisper encoder penceresini ses uzunluğuna göre kısaltır.

Whisper her girdiyi 30 saniyeye pad'ler ve encoder'ı hep tam pencere üzerinde
çalıştırır. 4 saniyelik dikte de 30 saniyelik hesabı öder — M4'te ölçülen:

    4.7s ses  → 1322 ms
    26.5s ses → 1590 ms     (5.6x ses, sadece +%20 süre)

Pencereyi kısaltmak matematiksel olarak güvenli: pozisyonel embedding
sinüzoidal (`sinusoids(n_ctx, n_state)`), yani ilk N pozisyon her zaman
aynı değerlere sahip. Kısaltmak = diziyi baştan dilimlemek.

İKİ TUZAK (ikisi de ölçümle bulundu, ikisi de burada ele alınıyor):

1. **Sonsuz döngü.** Timestamp token'ları 30 saniyelik pencereye göre eğitilmiş.
   Pencere kısalınca decoder pencere dışına düşen timestamp'ler üretiyor,
   `transcribe()` içindeki seek döngüsü ilerleyemiyor ve süreç kilitleniyor
   (>3.5 dk ölçüldü). Çözüm: `without_timestamps=True` — dikte akışında
   segment zaman damgası zaten kullanılmıyor.

2. **Tekrar hallüsinasyonu.** Pencere içeriğe çok yakınsa model cümleyi
   tekrarlıyor. 4.7s ses / 6s pencere (1.3s marj) → cümle 3 kez tekrarlandı;
   7s pencere (2.3s marj) → temiz. Çözüm: MARGIN_S=3 sn sondaki sessizlik
   payı + tekrar tespiti olursa tam 30s pencere ile bir kez retry.
"""

from __future__ import annotations

import logging
import math
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Whisper sabitleri
FULL_WINDOW_S = 30
FRAMES_PER_S = 100          # HOP_LENGTH=160 @ 16kHz → 100 mel frame/sn
CTX_PER_S = 50              # encoder conv2 stride 2 → 50 audio token/sn

# Sondaki sessizlik payı. 2 sn'nin altında tekrar hallüsinasyonu gözlendi.
MARGIN_S = 3
# Alt sınır: çok kısa pencerede model "bitir" sinyalini yakalayamıyor.
MIN_WINDOW_S = 6
# Bu sürenin altındaki ses tam pencereyle çözülür. Ölçüm (2026-10-02, 1085
# gerçek dikte): 2-4sn seste kısa pencere kelimelerin %96'sını değiştirdi
# ("Test, deneme" → "Test döneme"), 10/15/20sn pencere de kurtarmadı.
# 4sn üstünde fark küçük ve yön karışık; 6sn+ seste kısa pencere tam
# pencereden İYİ (tam pencere son cümleyi düşürebiliyor).
SHORT_AUDIO_S = 4.0

# mlx-whisper modül seviyesinde global sabitler kullanıyor ve model nesnesi
# ModelHolder'da cache'leniyor — pencere değişimi süreç geneli bir mutasyon.
# RecordingService MLX'i tek thread'lik executor'da çalıştırıyor ama warm-up
# gibi yollar araya girebilir, o yüzden kilit şart.
_lock = threading.Lock()


def compute_window(duration_s: float) -> int:
    """Ses uzunluğuna göre encoder penceresi (saniye)."""
    if duration_s < SHORT_AUDIO_S:  # 0/negatif de buraya düşer
        return FULL_WINDOW_S
    return max(MIN_WINDOW_S, min(FULL_WINDOW_S, math.ceil(duration_s) + MARGIN_S))


@contextmanager
def encoder_window(model_path: str, window_s: int, dtype=None):
    """Encoder penceresini `window_s` yapar, çıkışta 30 saniyeye geri alır.

    Model nesnesi ModelHolder'da cache'lendiği için mutasyon kalıcı olur —
    bu yüzden `finally` bloğunda restore ZORUNLU, aksi halde bir sonraki
    çağrı yanlış pencereyle çalışır.
    """
    import sys

    import mlx.core as mx
    import mlx_whisper.transcribe  # noqa: F401 — modülü sys.modules'a koymak için

    transcribe_mod = sys.modules["mlx_whisper.transcribe"]
    from mlx_whisper.whisper import sinusoids

    if dtype is None:
        dtype = mx.float16

    if window_s >= FULL_WINDOW_S:
        yield
        return

    with _lock:
        model = transcribe_mod.ModelHolder.get_model(model_path, dtype)
        prev_frames = transcribe_mod.N_FRAMES
        prev_samples = transcribe_mod.N_SAMPLES
        prev_ctx = model.dims.n_audio_ctx
        prev_pos = model.encoder._positional_embedding
        try:
            n_ctx = window_s * CTX_PER_S
            transcribe_mod.N_FRAMES = window_s * FRAMES_PER_S
            transcribe_mod.N_SAMPLES = window_s * 16000
            model.dims.n_audio_ctx = n_ctx
            model.encoder._positional_embedding = sinusoids(
                n_ctx, model.dims.n_audio_state
            ).astype(dtype)
            yield
        finally:
            transcribe_mod.N_FRAMES = prev_frames
            transcribe_mod.N_SAMPLES = prev_samples
            model.dims.n_audio_ctx = prev_ctx
            model.encoder._positional_embedding = prev_pos


def has_repeated_span(text: str, min_words: int = 4, max_words: int = 15) -> bool:
    """Uzun bir kelime dizisi ardışık tekrarlanıyor mu?

    `_strip_hallucination_loop` 1-3 gram'a bakıyor; kısa pencerenin ürettiği
    hata tüm CÜMLEnin tekrarı (8+ kelime) olduğu için orada yakalanmıyor.
    """
    words = text.split()
    for n in range(min_words, min(max_words, len(words) // 2) + 1):
        for i in range(len(words) - 2 * n + 1):
            if words[i:i + n] == words[i + n:i + 2 * n]:
                logger.warning(
                    "Repeated %d-word span detected: %r", n, " ".join(words[i:i + n])
                )
                return True
    return False
