"""Uzun sesi sessizlikten bölme — saf fonksiyon testleri (model gerektirmez).

Neden: fine-tune model (ISSAI kısa cümleleri) uzun seste parça atlıyordu —
eval'de 7 kayıtta 4+ kelimelik parça düştü, base modelde 1. Kısa parçalar
modelin eğitildiği dağılıma yakın.
"""

import numpy as np
import pytest

from voiceflow.transcription.chunking import split_on_silence

SR = 16000


def tone(seconds: float) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    return (0.1 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SR), dtype=np.float32)


def speech_with_gaps(parts: list[float], gap: float = 0.6) -> tuple[np.ndarray, list[float]]:
    """Konuşma blokları arasında sessizlik; boşlukların orta noktalarını döndür (sn)."""
    chunks, gaps, t = [], [], 0.0
    for i, p in enumerate(parts):
        chunks.append(tone(p)); t += p
        if i < len(parts) - 1:
            chunks.append(silence(gap)); gaps.append(t + gap / 2); t += gap
    return np.concatenate(chunks), gaps


class TestSplitOnSilence:
    def test_short_audio_is_single_span(self):
        audio = tone(8.0)
        assert split_on_silence(audio, SR, max_s=12) == [(0, len(audio))]

    def test_spans_are_contiguous_and_cover_everything(self):
        audio, _ = speech_with_gaps([5, 6, 4, 7, 5, 6])
        spans = split_on_silence(audio, SR, max_s=12)
        assert spans[0][0] == 0 and spans[-1][1] == len(audio)
        for (_, e), (s, _) in zip(spans, spans[1:]):
            assert e == s

    def test_cuts_land_in_silence(self):
        audio, gaps = speech_with_gaps([5, 6, 4, 7, 5, 6])
        spans = split_on_silence(audio, SR, max_s=12)
        for _, end in spans[:-1]:
            cut_s = end / SR
            assert min(abs(cut_s - g) for g in gaps) < 0.35, f"kesim konuşmanın ortasında: {cut_s:.2f}s"

    def test_no_span_exceeds_max_except_merged_tail(self):
        audio, _ = speech_with_gaps([5, 6, 4, 7, 5, 6])
        spans = split_on_silence(audio, SR, max_s=12, min_s=3)
        for s, e in spans:
            assert (e - s) / SR <= 12 + 3 + 0.01

    def test_tiny_tail_is_merged_into_previous(self):
        audio, _ = speech_with_gaps([11, 1])  # 12.6sn: son 1sn ayrı parça olmamalı
        spans = split_on_silence(audio, SR, max_s=12, min_s=3)
        assert len(spans) == 1

    def test_continuous_speech_still_splits_at_max(self):
        audio = tone(30.0)  # hiç sessizlik yok → yine de bölünmeli
        spans = split_on_silence(audio, SR, max_s=12)
        assert len(spans) >= 3
        assert all((e - s) / SR <= 15.01 for s, e in spans)
        # sessizlik yoksa max'a yakın kesmeli, 3sn'lik kırıntılar üretmemeli
        assert all((e - s) / SR >= 10 for s, e in spans[:-1])

    @pytest.mark.parametrize("n", [0, 10])
    def test_empty_or_tiny_audio(self, n):
        audio = np.zeros(n, dtype=np.float32)
        assert split_on_silence(audio, SR, max_s=12) == ([(0, n)] if n else [])
