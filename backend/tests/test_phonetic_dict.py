"""Unit tests for dictionary phonetic matching (K4-P1).

Tests the apply_dictionary function with:
- Single-word triggers (standard usage)
- Multi-word phonetic triggers ("ant row pick" → "Anthropic")
- Turkish phonetic entries ("apvyumodel" → "AppViewModel")
- Partial match guard (no false positives)
- Longer-trigger-first ordering (no clobber)
"""

import pytest
from voiceflow.services.dictionary import apply_dictionary


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def entry(trigger: str, replacement: str) -> dict:
    return {"trigger": trigger, "replacement": replacement, "scope": "personal"}


# ---------------------------------------------------------------------------
# Single-word standard entries
# ---------------------------------------------------------------------------

def test_single_word_basic():
    entries = [entry("apvyumodel", "AppViewModel")]
    assert apply_dictionary("apvyumodel icinde state tutuyoruz", entries) == "AppViewModel icinde state tutuyoruz"


def test_single_word_case_insensitive():
    entries = [entry("APVYUMODEL", "AppViewModel")]
    assert apply_dictionary("apvyumodel baska bir sey", entries) == "AppViewModel baska bir sey"


def test_single_word_no_partial_match():
    """'pick' trigger must not match inside 'picking'."""
    entries = [entry("pick", "seç")]
    result = apply_dictionary("picking some items", entries)
    assert "picking" in result  # should not have been replaced


# ---------------------------------------------------------------------------
# Multi-word phonetic entries
# ---------------------------------------------------------------------------

def test_phonetic_multi_word_english():
    """'ant row pick' → 'Anthropic'."""
    entries = [entry("ant row pick", "Anthropic")]
    assert apply_dictionary("ant row pick is a great company", entries) == "Anthropic is a great company"


def test_phonetic_multi_word_turkish():
    """Turkish phonetic: 'apvyumodel' → 'AppViewModel' (single-word variant)."""
    entries = [entry("apvyumodel", "AppViewModel")]
    result = apply_dictionary("apvyumodel ile calısıyoruz", entries)
    assert result == "AppViewModel ile calısıyoruz"


def test_phonetic_multi_word_sentence():
    """Multi-word phonetic in middle of sentence."""
    entries = [entry("kway ree in struct", "QueryInstructor")]
    result = apply_dictionary("simdi kway ree in struct kullanıyorum", entries)
    assert "QueryInstructor" in result


def test_phonetic_case_insensitive():
    """Phonetic trigger matching is case-insensitive."""
    entries = [entry("Ant Row Pick", "Anthropic")]
    result = apply_dictionary("ant row pick ile konuşuyorum", entries)
    assert "Anthropic" in result


# ---------------------------------------------------------------------------
# Longer trigger takes priority
# ---------------------------------------------------------------------------

def test_longer_trigger_first():
    """Longer phrase must be matched before shorter sub-phrase."""
    entries = [
        entry("row", "satır"),
        entry("ant row pick", "Anthropic"),
    ]
    result = apply_dictionary("ant row pick modeli", entries)
    # "ant row pick" should match first — "row" inside it should not be replaced
    assert "Anthropic" in result
    assert "satır" not in result


# ---------------------------------------------------------------------------
# No-match cases
# ---------------------------------------------------------------------------

def test_no_entries_returns_original():
    text = "herhangi bir şey"
    assert apply_dictionary(text, []) == text


def test_empty_trigger_skipped():
    entries = [entry("", "replacement")]
    text = "bir şey"
    assert apply_dictionary(text, entries) == text


def test_empty_replacement_skipped():
    entries = [entry("trigger", "")]
    text = "trigger kelimesi"
    assert apply_dictionary(text, entries) == text


# ---------------------------------------------------------------------------
# Integration: /api/stop works without dictionary entries
# ---------------------------------------------------------------------------

def test_apply_dictionary_empty_text():
    entries = [entry("test", "TEST")]
    assert apply_dictionary("", entries) == ""
