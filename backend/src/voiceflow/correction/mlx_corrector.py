"""Local LLM correction using Apple MLX (mlx-lm) — runs on-device via Metal GPU."""

import gc
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import mlx.core as mx

from ..core import config as _cfg
from .prompts import (
    BASE_PROMPT, MODE_SUFFIXES, BaseCorrectorConfig,
    build_messages, build_system_prompt, guard_output, pre_process,
)

logger = logging.getLogger(__name__)

# Output format suffixes — MLX corrector only (API corrector uses prose only)
_OUTPUT_FORMAT_SUFFIXES: dict[str, str] = {
    "prose": "",
    "code_comment": (
        "\nFormat the corrected output as a code comment. "
        "Start with // and keep it concise (single line if possible)."
    ),
    "pr_description": (
        "\nFormat the corrected output as a GitHub Pull Request description using markdown. "
        "Include ## Summary and ## Changes sections with bullet points."
    ),
    "jira_ticket": (
        "\nFormat the corrected output as a Jira ticket. "
        "Include *Summary:*, *Description:*, and *Acceptance Criteria:* fields."
    ),
}

_SYSTEM_PROMPTS = {
    mode: BASE_PROMPT + suffix
    for mode, suffix in MODE_SUFFIXES.items()
}

# CJK and other non-Latin/Turkish character pattern (hallucination guard)
_NON_LATIN_TR = re.compile(
    r'[^\u0000-\u024F\u011E\u011F\u0130\u0131\u015E\u015F\u00C7\u00E7\u00D6\u00F6\u00DC\u00FC\s]'
)


@dataclass
class MLXCorrectorConfig(BaseCorrectorConfig):
    """Configuration for the MLX (local, on-device) corrector."""

    model_name: str = "mlx-community/Qwen2.5-7B-Instruct-4bit"
    adapter_path: str | None = field(
        default_factory=lambda: str(_cfg.LLM_ADAPTER_PATH) if _cfg.LLM_ADAPTER_PATH else None
    )  # LoRA adapter; None → full prompt fallback


@dataclass
class MLXCorrector:
    """Corrects transcription text using a local MLX LLM (Apple Silicon, Metal GPU)."""

    config: MLXCorrectorConfig = field(default_factory=MLXCorrectorConfig)
    _model: Any = field(default=None, init=False, repr=False)
    _tokenizer: Any = field(default=None, init=False, repr=False)

    def _build_system_prompt(
        self,
        active_app: str | None,
        window_title: str | None,
        selected_text: str | None,
        context: list[str] | None,
    ) -> str:
        """Build the system prompt for this correction request.

        When a LoRA adapter is loaded, runtime modifiers are skipped —
        the adapter generalises better without them.
        """
        base = _SYSTEM_PROMPTS.get(self.config.mode, _SYSTEM_PROMPTS["general"])

        if self.config.adapter_path:
            logger.debug("Using adapter prompt (mode=%s)", self.config.mode)
            return base

        return build_system_prompt(
            base_prompt=base,
            mode=self.config.mode,
            active_app=active_app,
            window_title=window_title,
            selected_text=selected_text,
            context=context,
            output_format_suffix=_OUTPUT_FORMAT_SUFFIXES.get(self.config.output_format, ""),
        )

    def preload(self) -> None:
        """Lazy load model (+ optional LoRA adapter) on first use."""
        if self._model is None:
            from mlx_lm import load

            logger.info("Loading MLX model: %s", self.config.model_name)
            if self.config.adapter_path:
                logger.info("Loading LoRA adapter: %s", self.config.adapter_path)
                self._model, self._tokenizer = load(
                    self.config.model_name,
                    adapter_path=self.config.adapter_path,
                )
            else:
                self._model, self._tokenizer = load(self.config.model_name)
            logger.info("MLX model loaded")

    def unload(self) -> None:
        """Release model from Metal GPU memory."""
        if self._model is not None:
            logger.info("Unloading MLX model")
            self._model = None
            self._tokenizer = None
            gc.collect()
            mx.metal.clear_cache()
            logger.info("MLX model unloaded")

    def correct(
        self,
        text: str,
        language: str | None = None,  # noqa: ARG002 — reserved for future lang-routing
        context: list[str] | None = None,
        active_app: str | None = None,
        window_title: str | None = None,
        selected_text: str | None = None,
    ) -> str:
        """Correct raw Whisper transcription using the local MLX LLM.

        Returns corrected text, or original on failure / disabled.
        """
        if not self.config.enabled or not text or not text.strip():
            return text

        text = pre_process(text)
        if not text.strip():
            return text

        from mlx_lm import generate
        from mlx_lm.sample_utils import make_sampler

        self.preload()

        try:
            messages = build_messages(
                self._build_system_prompt(active_app, window_title, selected_text, context),
                text,
            )
            formatted = self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            raw = generate(
                self._model,
                self._tokenizer,
                prompt=formatted,
                max_tokens=self.config.max_tokens,
                sampler=make_sampler(temp=0.0),
            )
            mx.metal.clear_cache()

            # Strip CJK / non-Latin-Turkish hallucinations
            cleaned = _NON_LATIN_TR.sub("", raw.strip()).strip()

            corrected = guard_output(cleaned, text)
            if corrected is None:
                return text

            logger.info("MLX correction: '%s' → '%s'", text[:50], corrected[:50])
            return corrected

        except Exception as e:
            logger.error("MLX correction failed: %s", e, exc_info=True)
            return text
