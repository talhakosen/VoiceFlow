"""Unit tests for correction prompt improvements (K4-P0).

Tests verify that _BASE_PROMPT and _FEW_SHOT_EXAMPLES in both correctors
contain all required rules without executing LLM inference.
"""

from voiceflow.correction.llm_corrector import _BASE_PROMPT as LLM_BASE_PROMPT
from voiceflow.correction.llm_corrector import _FEW_SHOT_EXAMPLES as LLM_EXAMPLES
from voiceflow.correction.ollama_corrector import _BASE_PROMPT as OLLAMA_BASE_PROMPT
from voiceflow.correction.ollama_corrector import _FEW_SHOT_EXAMPLES as OLLAMA_EXAMPLES


# ---------------------------------------------------------------------------
# _BASE_PROMPT content checks
# ---------------------------------------------------------------------------

class TestLLMBasePrompt:
    def test_filler_word_removal_tr_mentioned(self):
        assert "yani" in LLM_BASE_PROMPT
        assert "şey" in LLM_BASE_PROMPT
        assert "hani" in LLM_BASE_PROMPT

    def test_filler_word_removal_en_mentioned(self):
        assert "um" in LLM_BASE_PROMPT
        assert "uh" in LLM_BASE_PROMPT

    def test_backtracking_tr_markers(self):
        assert "hayır yok yok" in LLM_BASE_PROMPT

    def test_backtracking_en_markers(self):
        assert "scratch that" in LLM_BASE_PROMPT

    def test_spoken_punctuation_tr(self):
        assert "virgül" in LLM_BASE_PROMPT
        assert "nokta" in LLM_BASE_PROMPT

    def test_spoken_punctuation_en(self):
        assert "comma" in LLM_BASE_PROMPT
        assert "period" in LLM_BASE_PROMPT

    def test_hallucination_guard(self):
        assert "Never insert" in LLM_BASE_PROMPT or "never insert" in LLM_BASE_PROMPT.lower()

    def test_no_ideas_rule(self):
        assert "did not say" in LLM_BASE_PROMPT


class TestOllamaBasePrompt:
    def test_filler_word_removal_tr_mentioned(self):
        assert "yani" in OLLAMA_BASE_PROMPT
        assert "şey" in OLLAMA_BASE_PROMPT
        assert "hani" in OLLAMA_BASE_PROMPT

    def test_filler_word_removal_en_mentioned(self):
        assert "um" in OLLAMA_BASE_PROMPT
        assert "uh" in OLLAMA_BASE_PROMPT

    def test_backtracking_tr_markers(self):
        assert "hayır yok yok" in OLLAMA_BASE_PROMPT

    def test_backtracking_en_markers(self):
        assert "scratch that" in OLLAMA_BASE_PROMPT

    def test_spoken_punctuation_tr(self):
        assert "virgül" in OLLAMA_BASE_PROMPT
        assert "nokta" in OLLAMA_BASE_PROMPT

    def test_spoken_punctuation_en(self):
        assert "comma" in OLLAMA_BASE_PROMPT
        assert "period" in OLLAMA_BASE_PROMPT

    def test_hallucination_guard(self):
        assert "Never insert" in OLLAMA_BASE_PROMPT or "never insert" in OLLAMA_BASE_PROMPT.lower()

    def test_no_ideas_rule(self):
        assert "did not say" in OLLAMA_BASE_PROMPT


# ---------------------------------------------------------------------------
# Few-shot example coverage checks
# ---------------------------------------------------------------------------

def _get_inputs(examples: list) -> list[str]:
    return [inp for inp, _ in examples]


def _get_outputs(examples: list) -> list[str]:
    return [out for _, out in examples]


class TestLLMFewShotExamples:
    def test_has_filler_word_removal_tr(self):
        """At least one example should demonstrate TR filler removal."""
        inputs = _get_inputs(LLM_EXAMPLES)
        has_filler = any(
            any(f in inp for f in ["yani", "şey", "hani", "işte", "ee", "aa"])
            for inp in inputs
        )
        assert has_filler, "No Turkish filler word example found in few-shot"

    def test_has_filler_word_removal_en(self):
        """At least one example should demonstrate EN filler removal."""
        inputs = _get_inputs(LLM_EXAMPLES)
        has_filler = any(
            any(f in inp for f in ["um ", "uh ", " like ", "you know"])
            for inp in inputs
        )
        assert has_filler, "No English filler word example found in few-shot"

    def test_has_backtracking_tr(self):
        """At least one example should demonstrate Turkish backtracking."""
        inputs = _get_inputs(LLM_EXAMPLES)
        has_backtrack = any(
            any(m in inp for m in ["hayır yok yok", "dur bir dakika", "pardon"])
            for inp in inputs
        )
        assert has_backtrack, "No Turkish backtracking example found in few-shot"

    def test_has_backtracking_en(self):
        """At least one example should demonstrate English backtracking."""
        inputs = _get_inputs(LLM_EXAMPLES)
        has_backtrack = any("scratch that" in inp or "actually" in inp for inp in inputs)
        assert has_backtrack, "No English backtracking example found in few-shot"

    def test_has_spoken_punctuation_tr(self):
        """At least one example should demonstrate Turkish spoken punctuation."""
        inputs = _get_inputs(LLM_EXAMPLES)
        has_punct = any("virgül" in inp or "nokta" in inp for inp in inputs)
        assert has_punct, "No Turkish spoken punctuation example found in few-shot"

    def test_has_spoken_punctuation_en(self):
        """At least one example should demonstrate English spoken punctuation."""
        inputs = _get_inputs(LLM_EXAMPLES)
        has_punct = any("comma" in inp or " period" in inp for inp in inputs)
        assert has_punct, "No English spoken punctuation example found in few-shot"

    def test_backtracking_output_omits_retracted_part(self):
        """Backtracking output should NOT contain the retracted phrase."""
        for inp, out in LLM_EXAMPLES:
            if "hayır yok yok" in inp:
                # The part before the backtrack marker should not appear verbatim
                retracted = inp.split("hayır yok yok")[0].strip()
                assert retracted not in out, f"Retracted part '{retracted}' still in output"
            if "scratch that" in inp:
                retracted = inp.split("scratch that")[0].strip()
                assert retracted not in out, f"Retracted part '{retracted}' still in output"

    def test_spoken_punctuation_symbol_in_output(self):
        """Spoken punctuation input must produce symbol in output."""
        for inp, out in LLM_EXAMPLES:
            if "virgül" in inp:
                assert "," in out, "Expected ',' in output for 'virgül' input"
            if "nokta" in inp and inp != "nokta":
                assert "." in out, "Expected '.' in output for 'nokta' input"
            if "comma" in inp:
                assert "," in out, "Expected ',' in output for 'comma' input"


class TestOllamaFewShotExamples:
    def test_has_filler_word_removal_tr(self):
        inputs = _get_inputs(OLLAMA_EXAMPLES)
        has_filler = any(
            any(f in inp for f in ["yani", "şey", "hani", "işte", "ee", "aa"])
            for inp in inputs
        )
        assert has_filler

    def test_has_filler_word_removal_en(self):
        inputs = _get_inputs(OLLAMA_EXAMPLES)
        has_filler = any(
            any(f in inp for f in ["um ", "uh ", " like ", "you know"])
            for inp in inputs
        )
        assert has_filler

    def test_has_backtracking_tr(self):
        inputs = _get_inputs(OLLAMA_EXAMPLES)
        has_backtrack = any(
            any(m in inp for m in ["hayır yok yok", "dur bir dakika", "pardon"])
            for inp in inputs
        )
        assert has_backtrack

    def test_has_backtracking_en(self):
        inputs = _get_inputs(OLLAMA_EXAMPLES)
        has_backtrack = any("scratch that" in inp for inp in inputs)
        assert has_backtrack

    def test_has_spoken_punctuation_tr(self):
        inputs = _get_inputs(OLLAMA_EXAMPLES)
        has_punct = any("virgül" in inp or "nokta" in inp for inp in inputs)
        assert has_punct

    def test_has_spoken_punctuation_en(self):
        inputs = _get_inputs(OLLAMA_EXAMPLES)
        has_punct = any("comma" in inp or " period" in inp for inp in inputs)
        assert has_punct
