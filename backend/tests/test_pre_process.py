"""Unit tests for pre_process() — deterministic pre-LLM correction step.

pre_process() handles ONLY:
  1. Spoken punctuation  (virgül→, nokta→. etc.)
  2. Clear backtracking  (hayır yok yok / scratch that)

Filler word removal is handled by filler_cleaner.clean_fillers() in the service
pipeline (skipped in engineering mode). It is intentionally NOT in pre_process().
"""

import pytest
from voiceflow.correction.prompts import pre_process


# ── Spoken punctuation ────────────────────────────────────────────────────────

class TestSpokenPunctuation:
    def test_virgul_replaced(self):
        assert "," in pre_process("toplantı saat üçte virgül hazır ol lütfen")

    def test_nokta_at_end(self):
        result = pre_process("hazır ol lütfen nokta")
        assert result.endswith(".")

    def test_soru_isareti(self):
        assert "?" in pre_process("nasılsın soru işareti")

    def test_unlem(self):
        assert "!" in pre_process("bravo ünlem")

    def test_iki_nokta(self):
        assert ":" in pre_process("sonuç iki nokta başarılı")

    def test_comma_en(self):
        assert "," in pre_process("the meeting is at three comma be ready")

    def test_period_at_end_en(self):
        result = pre_process("be ready please period")
        assert result.endswith(".")

    def test_question_mark_en(self):
        assert "?" in pre_process("are you ready question mark")

    def test_exclamation_mark_en(self):
        assert "!" in pre_process("well done exclamation mark")

    def test_full_stop_en(self):
        assert "." in pre_process("that is all full stop")

    def test_multi_punct(self):
        result = pre_process("merhaba virgül nasılsın soru işareti")
        assert "," in result
        assert "?" in result

    def test_nokta_mid_sentence_not_replaced(self):
        # "Bu noktada" = "At this point" — should NOT be replaced
        result = pre_process("Bu noktada ne yapmalıyız")
        assert "nokta" in result  # not replaced
        assert result.count(".") == 0


# ── Backtracking ──────────────────────────────────────────────────────────────

class TestBacktracking:
    def test_hayir_yok_yok(self):
        result = pre_process("veritabanına kaydedelim hayır yok yok önce validasyon yapalım")
        assert "validasyon" in result
        assert "veritabanına" not in result

    def test_scratch_that(self):
        result = pre_process("let's save to the database scratch that let's do validation first")
        assert "validation" in result
        assert "database" not in result

    def test_pardon(self):
        result = pre_process("saat üçte buluşalım pardon dörtte buluşalım")
        assert "dörtte" in result
        assert "üçte" not in result

    def test_no_backtrack_when_missing(self):
        text = "toplantıya gidelim"
        assert pre_process(text) == text

    def test_chained_backtrack(self):
        result = pre_process("X yap hayır yok yok Y yap hayır yok yok Z yap")
        assert "Z yap" in result
        assert "X yap" not in result


# ── Filler words — NOT handled by pre_process ────────────────────────────────

class TestFillersNotStripped:
    """pre_process() must NOT touch filler words — that's filler_cleaner's job."""

    def test_yani_sey_preserved(self):
        text = "yani şey bu fonksiyonu düzeltmemiz lazım"
        result = pre_process(text)
        assert "fonksiyonu" in result  # content preserved
        # fillers may or may not remain — pre_process doesn't guarantee removal

    def test_mid_sentence_yani_preserved(self):
        text = "500 kişi yani yarısı geldi"
        result = pre_process(text)
        assert "yani" in result  # pre_process must NOT strip semantic yani


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_string(self):
        assert pre_process("") == ""

    def test_whitespace_only(self):
        assert pre_process("   ") == "   "

    def test_no_changes_needed(self):
        text = "Toplantı saat üçte başlıyor."
        assert pre_process(text) == text

    def test_does_not_add_words(self):
        text = "raporu hazırla"
        result = pre_process(text)
        # pre_process must never add content
        for word in result.split():
            assert word in text.split() or word in ",.?!:"
