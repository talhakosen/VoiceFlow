"""Server-mode LLM correction via Ollama (OpenAI-compatible API)."""

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_BASE_PROMPT = """\
You are a speech-to-text post-processor. The input is raw output from a speech recognition system (Whisper) — it may contain mishearings, missing punctuation, wrong words, or broken sentences.

Your job:
1. Detect the language (Turkish or English) and process accordingly.
2. For Turkish: fix Turkish characters (ç, ş, ğ, ı, ö, ü, İ), add correct punctuation and capitalization.
3. Correct words that were clearly misheard — use the surrounding context and any provided knowledge base context to determine the intended word.
4. Remove Turkish filler words and speech disfluencies: "gibi", "şey", "yani", "işte", "falan", "filan", "sanki", "hani", "ya", "ee", "öyle", "böyle" — ONLY when they are used as meaningless fillers (not when they carry actual meaning). For example: "gibi gibi gibi" → remove all; "test ediyorum gibi yaptım gibi" → "test ediyormuş gibi yaptım" (keep if meaningful).
5. Fix broken or incomplete sentences so they read naturally.
6. If the meaning is unclear or a word seems wrong, correct it to what was most likely intended.
7. Output ONLY the corrected text. No explanations, no commentary, no prefixes.
8. Do NOT add new sentences or ideas that were not in the original speech.
9. Keep the output in the same language as the input.\
"""

_MODE_SUFFIXES = {
    "general": "",
    "engineering": (
        "\n\nMode: Engineering. "
        "Preserve exact technical terms, class names, function names, variable names, API names, "
        "file paths, and CLI commands. Do not paraphrase or translate identifiers."
    ),
    "office": (
        "\n\nMode: Office/Business. "
        "Use formal register. Expand informal abbreviations (mrhb→merhaba, tşk→teşekkürler). "
        "Ensure professional tone suitable for business correspondence."
    ),
}

_SYSTEM_PROMPTS = {
    mode: _BASE_PROMPT + suffix
    for mode, suffix in _MODE_SUFFIXES.items()
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

_FEW_SHOT_EXAMPLES = [
    ("bugun hava cok guzel", "Bugün hava çok güzel."),
    ("apvyumodel icinde state tutuyoruz", "AppViewModel içinde state tutuyoruz."),
    ("toplanti saat uc te basliyo hazir ol lutfen", "Toplantı saat üçte başlıyor, hazır ol lütfen."),
    ("the api endpoint returns a json response we need to parse it", "The API endpoint returns a JSON response, we need to parse it."),
    ("yani sunu demek istiyorum eger kullanici giris yaparsa token uretmemiz gerekiyor", "Şunu demek istiyorum: eğer kullanıcı giriş yaparsa token üretmemiz gerekiyor."),
    ("şimdi sanki tekrar test ediyorum gibi yaptım gibi bakalım gibi mi", "Şimdi tekrar test ediyorum. Bakalım mı?"),
    ("bu seyi yani şey nasıl desem işte falan tamam gibi", "Bunu nasıl desem, tamam."),
]


@dataclass
class OllamaCorrectorConfig:
    """Ollama corrector configuration."""

    model_name: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "qwen2.5:7b"))
    llm_endpoint: str = field(default_factory=lambda: os.getenv("LLM_ENDPOINT", "http://localhost:11434"))
    api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
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

    async def correct_async(self, text: str, language: str | None = None, context: list[str] | None = None, active_app: str | None = None) -> str:
        """Async version — preferred in server mode to avoid blocking the MLX executor."""
        import httpx

        if not self.config.enabled or not text.strip():
            return text
        if language and language != "tr":
            return text

        system_prompt = _SYSTEM_PROMPTS.get(self.config.mode, _SYSTEM_PROMPTS["general"])
        if active_app:
            tone = _APP_TONE_MAP.get(active_app)
            if tone:
                system_prompt = system_prompt + _TONE_OVERRIDES[tone]
                logger.debug("Tone override '%s' applied for app: %s", tone, active_app)
        if context:
            context_block = "\n".join(f"- {chunk[:200]}" for chunk in context)
            system_prompt = system_prompt + f"\n\nRelevant context from company knowledge base:\n{context_block}"
        messages = [{"role": "system", "content": system_prompt}]
        for user_text, assistant_text in _FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": user_text})
            messages.append({"role": "assistant", "content": assistant_text})
        messages.append({"role": "user", "content": text})

        try:
            headers = {}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.config.llm_endpoint}/v1/chat/completions",
                    headers=headers,
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

    def correct(self, text: str, language: str | None = None, context: list[str] | None = None, active_app: str | None = None) -> str:
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
        if active_app:
            tone = _APP_TONE_MAP.get(active_app)
            if tone:
                system_prompt = system_prompt + _TONE_OVERRIDES[tone]
                logger.debug("Tone override '%s' applied for app: %s", tone, active_app)
        if context:
            context_block = "\n".join(f"- {chunk[:200]}" for chunk in context)
            system_prompt = system_prompt + f"\n\nRelevant context from company knowledge base:\n{context_block}"
        messages = [{"role": "system", "content": system_prompt}]
        for user_text, assistant_text in _FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": user_text})
            messages.append({"role": "assistant", "content": assistant_text})
        messages.append({"role": "user", "content": text})

        try:
            headers = {}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            response = httpx.post(
                f"{self.config.llm_endpoint}/v1/chat/completions",
                headers=headers,
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
