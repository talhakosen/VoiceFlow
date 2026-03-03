"""LLM-based text correction using mlx-lm."""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Convert ASCII Turkish text to proper Turkish with correct characters "
    "(ç,ş,ğ,ı,ö,ü,İ) and punctuation. Keep all words exactly the same."
)

_FEW_SHOT_EXAMPLES = [
    ("bugun hava cok guzel", "Bugün hava çok güzel."),
    ("turkiyede yasiyorum ve cok mutluyum", "Türkiye'de yaşıyorum ve çok mutluyum."),
    ("ben yarin is toplantisina gidecegim", "Ben yarın iş toplantısına gideceğim."),
]


@dataclass
class CorrectorConfig:
    """LLM corrector configuration."""

    model_name: str = "mlx-community/Qwen2.5-7B-Instruct-4bit"
    max_tokens: int = 512
    enabled: bool = False


@dataclass
class LLMCorrector:
    """Corrects transcription text using a local LLM."""

    config: CorrectorConfig = field(default_factory=CorrectorConfig)
    _model: Any = field(default=None, init=False, repr=False)
    _tokenizer: Any = field(default=None, init=False, repr=False)

    def _ensure_model_loaded(self) -> None:
        """Lazy load model on first use."""
        if self._model is None:
            from mlx_lm import load

            logger.info(f"Loading LLM model: {self.config.model_name}")
            self._model, self._tokenizer = load(self.config.model_name)
            logger.info("LLM model loaded successfully")

    def correct(self, text: str, language: str | None = None) -> str:
        """Correct transcription text using LLM.

        Args:
            text: Raw transcription text from Whisper
            language: Detected language code (e.g. "tr", "en")

        Returns:
            Corrected text, or original text if correction fails/skipped
        """
        if not self.config.enabled:
            return text

        if not text or not text.strip():
            return text

        # Only correct Turkish text
        if language and language != "tr":
            return text

        from mlx_lm import generate
        from mlx_lm.sample_utils import make_sampler

        self._ensure_model_loaded()

        try:
            messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
            for user_text, assistant_text in _FEW_SHOT_EXAMPLES:
                messages.append({"role": "user", "content": user_text})
                messages.append({"role": "assistant", "content": assistant_text})
            messages.append({"role": "user", "content": text})

            formatted = self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            corrected = generate(
                self._model,
                self._tokenizer,
                prompt=formatted,
                max_tokens=self.config.max_tokens,
                sampler=make_sampler(temp=0.0),
            )

            corrected = corrected.strip()

            # Safety: return original if output is empty or suspiciously long
            if not corrected:
                logger.warning("LLM returned empty output, using original text")
                return text

            if len(corrected) > len(text) * 1.5:
                logger.warning("LLM output too long (%.1fx), using original text",
                               len(corrected) / len(text))
                return text

            logger.info("Correction applied: '%s' -> '%s'", text[:50], corrected[:50])
            return corrected

        except Exception as e:
            logger.error(f"LLM correction failed: {e}")
            return text
