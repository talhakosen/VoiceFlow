"""Uzun sesi sessizlik noktalarından kısa parçalara böl.

Fine-tune Whisper (ISSAI kısa haber cümleleri) uzun seste erken "bitti" deyip
parça atlıyor: eval'de (2026-10-02, 121 etiketli dikte) 7 kayıtta 4+ kelimelik
parça düştü, base modelde 1. Parçaları modelin eğitildiği uzunluğa yaklaştırmak
bu kaybı önler. Kesimler en sessiz ana yapılır ki kelime ortadan bölünmesin.
"""

import numpy as np

_FRAME_S = 0.03     # RMS çerçevesi
_SMOOTH_S = 0.3     # tek bir sessiz çerçeve değil, kısa duraklama ara


def split_on_silence(
    audio: np.ndarray,
    sample_rate: int,
    max_s: float,
    min_s: float = 3.0,
) -> list[tuple[int, int]]:
    """Return contiguous (start, end) sample spans covering the whole audio.

    Each span is at most `max_s` long, cut at the quietest pause found in
    [min_s, max_s] from its start. A trailing piece shorter than `min_s` is
    merged into the previous span (so a span can reach max_s + min_s).
    """
    n = len(audio)
    if n == 0:
        return []
    max_n, min_n = int(max_s * sample_rate), int(min_s * sample_rate)
    if n <= max_n:
        return [(0, n)]

    frame = max(1, int(_FRAME_S * sample_rate))
    n_frames = n // frame
    rms = np.sqrt(np.mean(audio[: n_frames * frame].astype(np.float32).reshape(n_frames, frame) ** 2, axis=1))
    k = max(1, int(_SMOOTH_S / _FRAME_S))
    energy = np.convolve(rms, np.ones(k) / k, mode="same")

    spans: list[tuple[int, int]] = []
    start = 0
    while n - start > max_n:
        lo = (start + min_n) // frame
        hi = min((start + max_n) // frame, n_frames - 1)
        if hi > lo:
            # Eşitlikte en GEÇ nokta — sessizlik yoksa max'a yakın kes, minik parça üretme
            window = energy[lo:hi + 1][::-1]
            cut = (hi - int(np.argmin(window))) * frame + frame // 2
        else:
            cut = start + max_n
        spans.append((start, cut))
        start = cut
    if spans and n - start < min_n:
        spans[-1] = (spans[-1][0], n)
    else:
        spans.append((start, n))
    return spans
