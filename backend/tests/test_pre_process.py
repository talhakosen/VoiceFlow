"""Unit tests for pre_process() — deterministic pre-LLM correction step."""

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


# ── Filler chains ─────────────────────────────────────────────────────────────

class TestFillerChains:
    def test_yani_sey(self):
        result = pre_process("yani şey bu fonksiyonu düzeltmemiz lazım")
        assert "yani şey" not in result.lower()
        assert "fonksiyonu" in result

    def test_hani_yani(self):
        result = pre_process("hani yani toplantıya gidecektik")
        assert "hani yani" not in result.lower()
        assert "toplantıya" in result

    def test_iste_yani(self):
        result = pre_process("işte yani sorun bu")
        assert "işte yani" not in result.lower()
        assert "sorun" in result


# ── Sentence-starting fillers ─────────────────────────────────────────────────

class TestSentenceStartFillers:
    def test_yani_start(self):
        result = pre_process("Yani, bu toplantıya gitmemiz lazım")
        assert not result.lower().startswith("yani")
        assert "toplantıya" in result

    def test_sey_start(self):
        result = pre_process("şey, bunu nasıl yapacağız")
        assert not result.lower().startswith("şey")
        assert "bunu" in result

    def test_ee_start(self):
        result = pre_process("ee, neyse devam edelim")
        assert not result.lower().startswith("ee")
        assert "devam" in result

    def test_eee_start(self):
        result = pre_process("eee toplantı iptal oldu")
        assert not result.lower().startswith("eee")

    def test_no_strip_mid_sentence(self):
        # "yani" mid-sentence with semantic meaning should NOT be stripped by pre_process
        text = "500 kişi yani yarısı geldi"
        result = pre_process(text)
        assert "yani" in result  # context-sensitive — left for LLM


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
