"""Unit tests for correction prompt and pre-processor pipeline.

Architecture:
  pre_process() → deterministic (spoken punct, clear backtracks, simple fillers)
  BASE_PROMPT   → LLM instructions for what pre_process cannot handle
"""

from voiceflow.correction.prompts import BASE_PROMPT, FEW_SHOT_EXAMPLES, pre_process


# ---------------------------------------------------------------------------
# BASE_PROMPT content — verifies LLM instructions for remaining work
# ---------------------------------------------------------------------------

class TestBasePrompt:
    def test_context_sensitive_filler_keep_rule(self):
        """Prompt must instruct LLM to KEEP meaningful 'yani' / 'hani'."""
        assert "yani" in BASE_PROMPT
        assert "hani" in BASE_PROMPT

    def test_hallucination_guard(self):
        """Prompt must forbid inserting unsaid content."""
        lower = BASE_PROMPT.lower()
        assert "never insert" in lower or "not in the original" in lower or "did not say" in lower

    def test_no_answer_critical_rule(self):
        """Prompt must instruct LLM not to answer commands."""
        assert "CRITICAL" in BASE_PROMPT

    def test_turkish_char_rule(self):
        """Prompt must instruct LLM to fix Turkish characters."""
        assert "ç" in BASE_PROMPT or "ş" in BASE_PROMPT or "ğ" in BASE_PROMPT

    def test_misheard_correction_mentioned(self):
        """Prompt must mention misheard word correction."""
        lower = BASE_PROMPT.lower()
        assert "misheard" in lower or "correct" in lower

    def test_pre_process_acknowledged(self):
        """Prompt must acknowledge that pre-processing has already run."""
        lower = BASE_PROMPT.lower()
        assert "pre-process" in lower or "pre_process" in lower or "pre-processed" in lower


# ---------------------------------------------------------------------------
# Few-shot examples — verifies coverage of remaining LLM tasks
# ---------------------------------------------------------------------------

def _inputs(examples): return [i for i, _ in examples]
def _outputs(examples): return [o for _, o in examples]


class TestFewShotExamples:
    def test_has_turkish_char_example(self):
        """At least one example should show Turkish character correction."""
        inputs = _inputs(FEW_SHOT_EXAMPLES)
        assert any(
            any(c in inp for c in ["cok", "bugun", "basliyo", "icinde"])
            for inp in inputs
        )

    def test_has_misheard_correction(self):
        """At least one example should show misheard word correction."""
        inputs = _inputs(FEW_SHOT_EXAMPLES)
        assert any("apvyumodel" in inp or "apvu" in inp for inp in inputs)

    def test_has_context_sensitive_filler(self):
        """At least one example should show filler removal."""
        inputs = _inputs(FEW_SHOT_EXAMPLES)
        assert any(
            any(f in inp for f in ["yani", "şey", "hani", "işte", "ee", "um ", "uh "])
            for inp in inputs
        )

    def test_has_english_example(self):
        inputs = _inputs(FEW_SHOT_EXAMPLES)
        assert any(inp[0].islower() and inp.isascii() for inp in inputs)

    def test_outputs_never_empty(self):
        for _, out in FEW_SHOT_EXAMPLES:
            assert out.strip(), "Few-shot output must not be empty"

    def test_backtracking_output_omits_retracted(self):
        """Backtracking examples: retracted part must not appear in output."""
        for inp, out in FEW_SHOT_EXAMPLES:
            if "hayır yok yok" in inp:
                retracted = inp.split("hayır yok yok")[0].strip()
                assert retracted not in out
            if "scratch that" in inp:
                retracted = inp.split("scratch that")[0].strip()
                assert retracted not in out

    def test_spoken_punct_symbol_in_output(self):
        """Spoken-punct examples: symbol must appear in output."""
        for inp, out in FEW_SHOT_EXAMPLES:
            if "virgül" in inp:
                assert "," in out
            if "comma" in inp:
                assert "," in out


# ---------------------------------------------------------------------------
# Integration: pre_process + BASE_PROMPT cover the full rule set
# ---------------------------------------------------------------------------

class TestPipelineCoverage:
    """Verify that pre_process + LLM together handle the full rule set."""

    def test_spoken_punct_handled_by_preprocessor(self):
        result = pre_process("hazır ol lütfen nokta")
        assert result.endswith(".")

    def test_backtrack_handled_by_preprocessor(self):
        result = pre_process("kaydet hayır yok yok vazgeç")
        assert "kaydet" not in result

    def test_sentence_filler_handled_by_preprocessor(self):
        result = pre_process("Yani, toplantıya gidiyoruz")
        assert not result.lower().startswith("yani")

    def test_context_sensitive_filler_left_for_llm(self):
        """mid-sentence 'yani' as i.e. must NOT be stripped by pre_process."""
        result = pre_process("500 kişi yani yarısı geldi")
        assert "yani" in result
