"""Unit tests for the deterministic Turkish filler cleaner.

Runs on every general/office dictation — even with LLM correction off — so a
bug here is visible in raw output. It does not add punctuation (the LLM does).
"""

import pytest

from voiceflow.services.filler_cleaner import clean_fillers


class TestRemovesFillers:
    @pytest.mark.parametrize("raw, expected", [
        ("yani şey bu fonksiyonu düzeltmemiz lazım", "Bu fonksiyonu düzeltmemiz lazım"),
        ("şey toplantı saat üçte", "Toplantı saat üçte"),
        ("ee yarın görüşürüz", "Yarın görüşürüz"),
        ("hani bu fonksiyonu düzeltelim", "Bu fonksiyonu düzeltelim"),
        ("toplantıya gitmemiz gerekiyor yani", "Toplantıya gitmemiz gerekiyor"),
        ("rapor hazır yani şimdi gönderiyorum", "Rapor hazır şimdi gönderiyorum"),
    ])
    def test_removes(self, raw, expected):
        assert clean_fillers(raw) == expected


class TestKeepsMeaningfulWords:
    @pytest.mark.parametrize("raw", [
        "bir şey sormak istiyorum",
        "her şey yolunda",
        "500 kişi, yani yarısı geldi",
    ])
    def test_existing_protections(self, raw):
        assert raw.split()[0].lower() in clean_fillers(raw).lower()
        assert ("yani" in raw) == ("yani" in clean_fillers(raw))

    @pytest.mark.parametrize("raw, kept", [
        # "yani" = "i.e." before a quantity, written as words (Whisper often does)
        ("toplantıya beş yüz kişi geldi yani yarısı", "yani yarısı"),
        ("bütçe iki milyon yani yüzde on arttı", "yani yüzde"),
        ("altı ay yani iki çeyrek sürdü", "yani iki"),
    ])
    def test_yani_before_quantity(self, raw, kept):
        assert kept in clean_fillers(raw).lower()

    def test_yarin_is_not_a_quantity(self):
        # "yarı" (half) must not match "yarın" (tomorrow)
        assert "yani" not in clean_fillers("proje yani yarın teslim").lower()

    @pytest.mark.parametrize("raw, expected", [
        # "hani o/şu …" = "remember that …" — not a filler
        ("hani o toplantı vardı ya orada konuşmuştuk", "Hani o toplantı vardı ya orada konuşmuştuk"),
        ("hani şu müşteri geri döndü", "Hani şu müşteri geri döndü"),
    ])
    def test_hani_as_reminder(self, raw, expected):
        assert clean_fillers(raw) == expected


class TestTurkishCapitalization:
    @pytest.mark.parametrize("raw, expected", [
        # Python's str.upper() maps i → I; Turkish needs i → İ
        ("işte bu yüzden testleri yazmamız lazım", "İşte bu yüzden testleri yazmamız lazım"),
        ("yani istanbul'a gidiyoruz", "İstanbul'a gidiyoruz"),
        ("ılık bir gün", "Ilık bir gün"),
        ("çok güzel", "Çok güzel"),
    ])
    def test_first_letter(self, raw, expected):
        assert clean_fillers(raw) == expected


class TestSentenceStartAfterPunctuation:
    @pytest.mark.parametrize("raw, expected", [
        # Regresyon: "satılması? Yani bu" → "satılması?bu" (boşluk filler'la gidiyordu)
        ("satılması mı? Yani bu mesela yavaşlatır", "Satılması mı? Bu mesela yavaşlatır"),
        ("Tamam. Şey, yarın gelirim", "Tamam. Yarın gelirim"),
        ("Bitti! Ee işte gidelim", "Bitti! İşte gidelim"),
    ])
    def test_keeps_space_and_capitalizes(self, raw, expected):
        assert clean_fillers(raw) == expected
