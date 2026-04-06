"""Tests for voiceflow/indexing/ — one-time setup operations."""

from voiceflow.indexing.tech_lexicon import generate_triggers, split_pascal


class TestSplitPascal:
    def test_two_parts(self):
        assert split_pascal("UserService") == ["User", "Service"]

    def test_three_parts(self):
        assert split_pascal("PaymentRepository") == ["Payment", "Repository"]

    def test_single_word(self):
        assert split_pascal("Router") == ["Router"]

    def test_consecutive_caps(self):
        # XMLParser → ['XML', 'Parser']
        result = split_pascal("XMLParser")
        assert "Parser" in result


class TestGenerateTriggers:
    def test_returns_list(self):
        result = generate_triggers("UserService")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_contains_turkish_variant(self):
        result = generate_triggers("UserService")
        assert any("servis" in t for t in result)

    def test_contains_turkish_domain(self):
        result = generate_triggers("UserService")
        assert any("kullanıcı" in t for t in result)

    def test_no_empty_triggers(self):
        for t in generate_triggers("PaymentRepository"):
            assert len(t) >= 3

    def test_unknown_identifier_returns_lowercase(self):
        result = generate_triggers("Foobar")
        assert "foobar" in result

    def test_max_60_results(self):
        # Cartesian product is capped at 60
        assert len(generate_triggers("UserServiceRepository")) <= 60
