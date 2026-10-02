"""Dinamik Whisper encoder penceresi — saf fonksiyon testleri (model gerektirmez)."""

import pytest

from voiceflow.transcription.dynamic_window import (
    FULL_WINDOW_S,
    MARGIN_S,
    MIN_WINDOW_S,
    SHORT_AUDIO_S,
    compute_window,
    has_repeated_span,
)


class TestComputeWindow:
    @pytest.mark.parametrize("dur", [0.1, 1.5, 1.6, 3.0, 3.9])
    def test_short_audio_uses_full_window(self, dur):
        # Regresyon (2026-10-02): 4sn altı seste kısa pencere çıktıyı bozuyordu —
        # 60 kayıtta 54 fark, "Test, deneme" → "Test döneme", tekrar döngüleri.
        # 10/15/20sn pencere de kurtarmadı; yalnız tam pencere doğru.
        assert compute_window(dur) == FULL_WINDOW_S

    def test_short_audio_threshold(self):
        assert compute_window(SHORT_AUDIO_S - 0.01) == FULL_WINDOW_S
        assert compute_window(SHORT_AUDIO_S) < FULL_WINDOW_S

    def test_minimum_window_still_applies_above_threshold(self):
        assert compute_window(SHORT_AUDIO_S) >= MIN_WINDOW_S

    def test_typical_dictation_gets_margin(self):
        assert compute_window(4.7) == 8    # ceil(4.7)=5 + 3
        assert compute_window(8.8) == 12   # ceil(8.8)=9 + 3

    def test_margin_is_always_at_least_two_seconds(self):
        # 2sn altı marj tekrar hallüsinasyonu üretiyor (ölçüldü: 4.7s ses / 6s pencere)
        for dur in (3.0, 5.5, 9.9, 15.2, 20.0):
            window = compute_window(dur)
            if window < FULL_WINDOW_S:
                assert window - dur >= 2.0, f"{dur}s için marj yetersiz: {window}s"

    def test_long_audio_capped_at_full_window(self):
        assert compute_window(28.0) == FULL_WINDOW_S
        assert compute_window(30.0) == FULL_WINDOW_S
        assert compute_window(120.0) == FULL_WINDOW_S

    def test_never_exceeds_whisper_limit(self):
        for dur in range(0, 200, 3):
            assert compute_window(float(dur)) <= FULL_WINDOW_S

    @pytest.mark.parametrize("dur", [0.0, -1.0])
    def test_empty_or_invalid_falls_back_to_full(self, dur):
        assert compute_window(dur) == FULL_WINDOW_S

    def test_margin_constant_is_applied(self):
        assert compute_window(10.0) == 10 + MARGIN_S


class TestHasRepeatedSpan:
    def test_clean_text_is_not_flagged(self):
        assert not has_repeated_span(
            "Bugün toplantıda konuştuğumuz maddeleri özetleyip ekibe göndereceğim."
        )

    def test_repeated_sentence_is_flagged(self):
        # Gerçek regresyon: 4.7s ses / 6s pencere bu çıktıyı üretti
        text = (
            "Bugün toplantıda konuştuğumuz maddeleri özetleyip ekibe göndereceğim. "
            "Bugün toplantıda konuştuğumuz maddeleri özetleyip ekibe göndereceğim."
        )
        assert has_repeated_span(text)

    def test_short_repetition_below_threshold_is_ignored(self):
        # 1-3 gram tekrarları _strip_hallucination_loop'un işi, buranın değil
        assert not has_repeated_span("evet evet evet")

    def test_repetition_mid_text_is_flagged(self):
        text = "Merhaba nasılsın bugün hava çok güzel bugün hava çok güzel görüşürüz"
        assert has_repeated_span(text)

    def test_empty_and_tiny_inputs_are_safe(self):
        assert not has_repeated_span("")
        assert not has_repeated_span("tek")
        assert not has_repeated_span("iki kelime")

    def test_similar_but_not_identical_is_not_flagged(self):
        text = "birinci madde tamamlandı ikinci madde tamamlanmadı üçüncü madde bekliyor"
        assert not has_repeated_span(text)


class TestEncoderWindowRestore:
    """Pencere mutasyonu süreç geneli — restore edilmezse sonraki çağrı bozulur."""

    def test_full_window_is_a_noop(self):
        pytest.importorskip("mlx_whisper")
        import sys

        import mlx_whisper.transcribe  # noqa: F401

        from voiceflow.transcription.dynamic_window import encoder_window

        mod = sys.modules["mlx_whisper.transcribe"]
        before = (mod.N_FRAMES, mod.N_SAMPLES)
        with encoder_window("dummy-path", FULL_WINDOW_S):
            # 30s = pencere değişmez, model bile yüklenmez
            assert (mod.N_FRAMES, mod.N_SAMPLES) == before
        assert (mod.N_FRAMES, mod.N_SAMPLES) == before
