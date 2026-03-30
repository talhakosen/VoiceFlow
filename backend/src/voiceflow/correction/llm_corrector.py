"""LLM-based text correction using mlx-lm."""

import gc
import logging
from dataclasses import dataclass, field
from typing import Any

import mlx.core as mx

logger = logging.getLogger(__name__)

_SYSTEM_PROMPTS = {
    "general": (
        "Convert ASCII Turkish text to proper Turkish with correct characters "
        "(ç,ş,ğ,ı,ö,ü,İ) and punctuation. Keep all words exactly the same."
    ),
    "engineering": (
        "Convert ASCII Turkish text to proper Turkish with correct characters "
        "(ç,ş,ğ,ı,ö,ü,İ) and punctuation. "
        "Preserve all technical terms, API names, variable names, and acronyms verbatim. "
        "Do not translate or expand technical identifiers."
    ),
    "office": (
        "Convert ASCII Turkish text to proper Turkish with correct characters "
        "(ç,ş,ğ,ı,ö,ü,İ) and punctuation. "
        "Use formal register. Expand informal abbreviations (mrhb→merhaba, tşk→teşekkürler). "
        "Ensure professional tone suitable for business communication."
    ),
}

# Tone suffixes appended to the base system prompt based on active app
_TONE_OVERRIDES = {
    "formal": (
        " Use formal, polished language suitable for professional correspondence. "
        "Full sentences, no abbreviations."
    ),
    "casual": (
        " Use natural, conversational language. Short sentences are fine."
    ),
    "technical": (
        " Preserve all technical terms, commands, paths, and identifiers exactly as spoken. "
        "Do not paraphrase or expand CLI commands."
    ),
}

# Bundle ID → tone mapping
_APP_TONE_MAP: dict[str, str] = {
    "com.apple.mail": "formal",
    "com.microsoft.Outlook": "formal",
    "com.apple.Notes": "casual",
    "com.tinyspeck.slackmacgap": "casual",
    "com.discord": "casual",
    "com.apple.Terminal": "technical",
    "com.microsoft.VSCode": "technical",
    "com.googlecode.iterm2": "technical",
    "com.jetbrains.intellij": "technical",
    "com.jetbrains.pycharm": "technical",
}

_SYSTEM_PROMPT = _SYSTEM_PROMPTS["general"]  # backward compat

# Output format suffixes — appended to system prompt when engineering mode is active
_OUTPUT_FORMAT_SUFFIXES: dict[str, str] = {
    "prose": "",  # default — no change
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
    mode: str = "general"  # "general" | "engineering" | "office"
    output_format: str = "prose"  # "prose" | "code_comment" | "pr_description" | "jira_ticket"


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

    def unload(self) -> None:
        """Unload model from memory."""
        if self._model is not None:
            logger.info("Unloading LLM model")
            self._model = None
            self._tokenizer = None
            gc.collect()
            mx.metal.clear_cache()
            logger.info("LLM model unloaded")

    def correct(self, text: str, language: str | None = None, context: list[str] | None = None, active_app: str | None = None) -> str:
        """Correct transcription text using LLM.

        Args:
            text: Raw transcription text from Whisper
            language: Detected language code (e.g. "tr", "en")
            context: Optional RAG context chunks to inject into the system prompt.

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
            system_prompt = _SYSTEM_PROMPTS.get(self.config.mode, _SYSTEM_PROMPTS["general"])
            # Tone override based on active app (independent of mode)
            if active_app:
                tone = _APP_TONE_MAP.get(active_app)
                if tone:
                    system_prompt = system_prompt + _TONE_OVERRIDES[tone]
                    logger.debug("Tone override '%s' applied for app: %s", tone, active_app)
            # Output format suffix (engineering mode feature)
            fmt_suffix = _OUTPUT_FORMAT_SUFFIXES.get(self.config.output_format, "")
            if fmt_suffix:
                system_prompt = system_prompt + fmt_suffix
            if context:
                context_block = "\n".join(f"- {chunk[:200]}" for chunk in context)
                system_prompt = system_prompt + f"\n\nRelevant context from company knowledge base:\n{context_block}"
            messages = [{"role": "system", "content": system_prompt}]
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

            # Free Metal GPU buffers to prevent memory growth
            mx.metal.clear_cache()

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
