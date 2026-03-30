"""Server-mode LLM correction via Ollama (OpenAI-compatible API)."""

import logging
import os
from dataclasses import dataclass, field

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

_SYSTEM_PROMPT = _SYSTEM_PROMPTS["general"]  # backward compat

_FEW_SHOT_EXAMPLES = [
    ("bugun hava cok guzel", "Bugün hava çok güzel."),
    ("turkiyede yasiyorum ve cok mutluyum", "Türkiye'de yaşıyorum ve çok mutluyum."),
    ("ben yarin is toplantisina gidecegim", "Ben yarın iş toplantısına gideceğim."),
]


@dataclass
class OllamaCorrectorConfig:
    """Ollama corrector configuration."""

    model_name: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "qwen2.5:7b"))
    llm_endpoint: str = field(default_factory=lambda: os.getenv("LLM_ENDPOINT", "http://localhost:11434"))
    max_tokens: int = 512
    enabled: bool = False
    mode: str = "general"  # "general" | "engineering" | "office"


@dataclass
class OllamaCorrector:
    """Corrects transcription text via Ollama's OpenAI-compatible API.

    Works with any OpenAI-compatible endpoint:
    - Ollama: http://ollama:11434
    - mlx-lm server: http://localhost:8080
    - vLLM: http://vllm:8000
    """

    config: OllamaCorrectorConfig = field(default_factory=OllamaCorrectorConfig)

    def _ensure_model_loaded(self) -> None:
        """Pre-warm Ollama — keeps model resident in GPU memory."""
        import httpx

        try:
            httpx.post(
                f"{self.config.llm_endpoint}/api/generate",
                json={"model": self.config.model_name, "keep_alive": -1},
                timeout=10.0,
            )
            logger.info("Ollama model pre-warmed: %s", self.config.model_name)
        except Exception as e:
            logger.warning("Ollama pre-warm failed (server may not be running yet): %s", e)

    def unload(self) -> None:
        """No-op — Ollama manages its own lifecycle."""
        pass

    async def correct_async(self, text: str, language: str | None = None, context: list[str] | None = None) -> str:
        """Async version — preferred in server mode to avoid blocking the MLX executor."""
        import httpx

        if not self.config.enabled or not text.strip():
            return text
        if language and language != "tr":
            return text

        system_prompt = _SYSTEM_PROMPTS.get(self.config.mode, _SYSTEM_PROMPTS["general"])
        if context:
            context_block = "\n".join(f"- {chunk[:200]}" for chunk in context)
            system_prompt = system_prompt + f"\n\nRelevant context from company knowledge base:\n{context_block}"
        messages = [{"role": "system", "content": system_prompt}]
        for user_text, assistant_text in _FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": user_text})
            messages.append({"role": "assistant", "content": assistant_text})
        messages.append({"role": "user", "content": text})

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.config.llm_endpoint}/v1/chat/completions",
                    json={
                        "model": self.config.model_name,
                        "messages": messages,
                        "temperature": 0.0,
                        "max_tokens": self.config.max_tokens,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                choices = response.json().get("choices", [])
                if not choices:
                    logger.warning("Ollama returned empty choices, using original")
                    return text
                corrected = choices[0]["message"]["content"].strip()

            if not corrected:
                logger.warning("Ollama returned empty output, using original")
                return text
            if len(corrected) > len(text) * 1.5:
                logger.warning("Ollama output too long (%.1fx), using original", len(corrected) / len(text))
                return text

            logger.info("Ollama correction: '%s' -> '%s'", text[:50], corrected[:50])
            return corrected

        except Exception as e:
            logger.error("Ollama async correction failed: %s", e)
            return text

    def correct(self, text: str, language: str | None = None, context: list[str] | None = None) -> str:
        """Correct transcription text via Ollama.

        Args:
            text: Raw transcription from Whisper
            language: Detected language code (only "tr" is corrected)
            context: Optional RAG context chunks to inject into the system prompt.

        Returns:
            Corrected text, or original on failure
        """
        import httpx

        if not self.config.enabled or not text.strip():
            return text

        if language and language != "tr":
            return text

        system_prompt = _SYSTEM_PROMPTS.get(self.config.mode, _SYSTEM_PROMPTS["general"])
        if context:
            context_block = "\n".join(f"- {chunk[:200]}" for chunk in context)
            system_prompt = system_prompt + f"\n\nRelevant context from company knowledge base:\n{context_block}"
        messages = [{"role": "system", "content": system_prompt}]
        for user_text, assistant_text in _FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": user_text})
            messages.append({"role": "assistant", "content": assistant_text})
        messages.append({"role": "user", "content": text})

        try:
            response = httpx.post(
                f"{self.config.llm_endpoint}/v1/chat/completions",
                json={
                    "model": self.config.model_name,
                    "messages": messages,
                    "temperature": 0.0,
                    "max_tokens": self.config.max_tokens,
                    "stream": False,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            corrected = response.json()["choices"][0]["message"]["content"].strip()

            if not corrected:
                logger.warning("Ollama returned empty output, using original")
                return text

            if len(corrected) > len(text) * 1.5:
                logger.warning(
                    "Ollama output too long (%.1fx), using original", len(corrected) / len(text)
                )
                return text

            logger.info("Ollama correction: '%s' -> '%s'", text[:50], corrected[:50])
            return corrected

        except Exception as e:
            logger.error("Ollama correction failed: %s", e)
            return text
