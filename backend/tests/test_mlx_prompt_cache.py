"""Unit tests for MLXCorrector prompt-cache orchestration.

The system prompt is a large constant prefix; we cache its KV once and only
process the per-request user text on later calls. These tests verify that
orchestration logic (split, build-once, trim-on-reuse, rebuild-on-change,
fallback, unload) WITHOUT loading a real model — all MLX calls are mocked.
"""

import sys
import types

import numpy as np
import pytest

from voiceflow.correction import mlx_corrector as mod
from voiceflow.correction.mlx_corrector import MLXCorrector, MLXCorrectorConfig


class _Block:
    """Stand-in for an mlx KVCache layer — only `.offset` matters here."""

    def __init__(self):
        self.offset = 0
        self.state = None  # read by mx.eval([blk.state for blk in cache])


@pytest.fixture
def spy(monkeypatch):
    """Patch every MLX call _generate_cached/_ensure_prefix_cache make, and
    record them so tests can assert on the orchestration."""
    calls = {"make": 0, "trim": [], "generate": []}

    # Fake mx: array(list) → ndarray (supports [None]); eval → no-op.
    fake_mx = types.SimpleNamespace(
        array=lambda x: np.asarray(x),
        eval=lambda *a, **k: None,
        metal=types.SimpleNamespace(clear_cache=lambda: None),
    )
    monkeypatch.setattr(mod, "mx", fake_mx)

    def make_prompt_cache(model):
        calls["make"] += 1
        return [_Block()]

    def trim_prompt_cache(cache, n):
        calls["trim"].append(n)
        cache[0].offset -= n

    def can_trim_prompt_cache(cache):
        return True

    cache_mod = types.ModuleType("mlx_lm.models.cache")
    cache_mod.make_prompt_cache = make_prompt_cache
    cache_mod.trim_prompt_cache = trim_prompt_cache
    cache_mod.can_trim_prompt_cache = can_trim_prompt_cache
    monkeypatch.setitem(sys.modules, "mlx_lm.models.cache", cache_mod)

    def generate(model, tokenizer, prompt=None, prompt_cache=None, max_tokens=None, sampler=None):
        calls["generate"].append({"prompt": prompt, "cached": prompt_cache is not None})
        if prompt_cache is not None:  # simulate request + generated tokens landing in cache
            prompt_cache[0].offset += 5
        return "OUTPUT"

    mlx_lm_mod = types.ModuleType("mlx_lm")
    mlx_lm_mod.generate = generate
    monkeypatch.setitem(sys.modules, "mlx_lm", mlx_lm_mod)

    sample_mod = types.ModuleType("mlx_lm.sample_utils")
    sample_mod.make_sampler = lambda temp=0.0: object()
    monkeypatch.setitem(sys.modules, "mlx_lm.sample_utils", sample_mod)

    return calls


def _corrector():
    c = MLXCorrector(config=MLXCorrectorConfig(enabled=True))
    # Fake model: forwarding tokens fills the cache by their count.
    def fake_model(tokens_2d, cache=None):
        if cache is not None:
            cache[0].offset += int(np.asarray(tokens_2d).shape[1])
    c._model = fake_model
    c._tokenizer = types.SimpleNamespace(encode=lambda s: [0] * max(1, len(s) // 4))
    return c


class TestPromptCache:
    def test_first_call_builds_cache_and_generates_suffix(self, spy):
        c = _corrector()
        prefix, text = "SYSTEM PROMPT user: ", "merhaba"
        out = c._generate_cached(prefix + text, text)

        assert out == "OUTPUT"
        assert spy["make"] == 1                       # cache built once
        assert c._cache_prefix == prefix              # remembers the prefix
        assert c._cache_prefix_len == len(c._tokenizer.encode(prefix))
        # generate ran on the suffix only, using the cache
        assert spy["generate"][0]["cached"] is True
        assert spy["generate"][0]["prompt"] == text

    def test_second_call_same_prefix_reuses_and_trims(self, spy):
        c = _corrector()
        prefix = "SYSTEM PROMPT user: "
        c._generate_cached(prefix + "first", "first")
        c._generate_cached(prefix + "second", "second")

        assert spy["make"] == 1                       # NOT rebuilt
        assert spy["trim"] == [5]                      # previous request's 5 tokens trimmed back off

    def test_prefix_change_rebuilds_cache(self, spy):
        c = _corrector()
        c._generate_cached("PROMPT A user: hi", "hi")
        c._generate_cached("PROMPT BBBB user: hi", "hi")  # different (longer) prefix

        assert spy["make"] == 2                       # rebuilt for the new prefix

    def test_fallback_when_text_not_in_prompt(self, spy):
        c = _corrector()
        out = c._generate_cached("a formatted prompt with no marker", "ZZZ")

        assert out == "OUTPUT"
        assert spy["make"] == 0                        # no cache path
        assert spy["generate"][0]["cached"] is False   # plain full generate
        assert spy["generate"][0]["prompt"] == "a formatted prompt with no marker"

    def test_unload_clears_cache_state(self, spy):
        c = _corrector()
        c._generate_cached("SYS user: x", "x")
        assert c._prompt_cache is not None

        c.unload()
        assert c._prompt_cache is None
        assert c._cache_prefix is None
        assert c._cache_prefix_len == 0


class TestModelConfig:
    def test_model_name_comes_from_config(self, monkeypatch):
        # config.yaml → llm.mlx_model; resolved at construction, not import time
        monkeypatch.setattr(mod._cfg, "LLM_MLX_MODEL", "org/some-model")
        assert MLXCorrectorConfig().model_name == "org/some-model"
