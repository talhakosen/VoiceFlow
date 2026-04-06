"""Server-mode LLM correction via Ollama (OpenAI-compatible API)."""

import logging
import os
from dataclasses import dataclass, field

from ..core import config as _cfg
from .prompts import MODE_SUFFIXES, build_messages, build_system_prompt

logger = logging.getLogger(__name__)

_BASE_PROMPT = """\
You are a speech-to-text post-processor. The input is raw output from a speech recognition system (Whisper) — it may contain mishearings, missing punctuation, wrong words, or broken sentences.

Your job:
1. Detect the language (Turkish or English) and process accordingly.
2. For Turkish: fix Turkish characters (ç, ş, ğ, ı, ö, ü, İ), add correct punctuation and capitalization.
3. Correct words that were clearly misheard — use the surrounding context and any provided knowledge base context to determine the intended word.
4. Remove filler words and speech disfluencies — ONLY when they carry no meaning:
   - Turkish fillers: yani, şey, hani, işte, ee, aa, falan, filen, gibi (filler), sanki (filler), öyle yani, vb.
   - English fillers: um, uh, like, you know, I mean (when used as filler), so (when used as filler at start)
   - Keep these words when they carry actual semantic meaning (e.g. "yani" meaning "that is", "gibi" as a real comparison, "like" as a comparison).
5. Handle backtracking and course corrections — the speaker may self-correct mid-sentence:
   - Turkish backtrack markers: "hayır yok yok", "dur bir dakika", "aslında", "yani şöyle", "pardon"
   - English backtrack markers: "scratch that", "actually", "wait", "I mean", "no wait", "let me rephrase"
   - When backtracking occurs, keep only the final intended statement. Discard the retracted portion.
6. Convert spoken punctuation to symbols:
   - "virgül" → , | "nokta" → . | "soru işareti" → ? | "ünlem" → ! | "iki nokta" → :
   - "comma" → , | "period" or "full stop" → . | "question mark" → ? | "exclamation mark" → !
7. Fix broken or incomplete sentences so they read naturally.
8. If the meaning is unclear or a word seems wrong, correct it to what was most likely intended.
9. Output ONLY the corrected text. No explanations, no commentary, no prefixes.
10. Do NOT add new sentences or ideas that were not in the original speech. Never insert names, terms, or words that the speaker did not say. Context is only for correcting spelling of words that were actually spoken.
11. Keep the output in the same language as the input.\
"""

_SYSTEM_PROMPTS = {
    mode: _BASE_PROMPT + suffix
    for mode, suffix in MODE_SUFFIXES.items()
}


@dataclass
class OllamaCorrectorConfig:
    """Ollama corrector configuration."""

    model_name: str = field(default_factory=lambda: _cfg.LLM_MODEL)
    llm_endpoint: str = field(default_factory=lambda: _cfg.LLM_ENDPOINT or "http://localhost:11434")
    api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    max_tokens: int = 512
    enabled: bool = False
    mode: str = "general"  # "general" | "engineering" | "office"
    output_format: str = "prose"

    def update(
        self,
        *,
        enabled: bool | None = None,
        mode: str | None = None,
        output_format: str | None = None,
    ) -> None:
        """Apply config changes atomically."""
        if enabled is not None:
            self.enabled = enabled
        if mode is not None:
            self.mode = mode
        if output_format is not None:
            self.output_format = output_format


@dataclass
class OllamaCorrector:
    """Corrects transcription text via Ollama's OpenAI-compatible API.

    Works with any OpenAI-compatible endpoint:
    - Ollama: http://ollama:11434
    - mlx-lm server: http://localhost:8080
    - vLLM: http://vllm:8000
    """

    config: OllamaCorrectorConfig = field(default_factory=OllamaCorrectorConfig)

    def _build_system_prompt(
        self,
        active_app: str | None,
        window_title: str | None,
        selected_text: str | None,
        context: list[str] | None,
    ) -> str:
        base = _SYSTEM_PROMPTS.get(self.config.mode, _SYSTEM_PROMPTS["general"])
        return build_system_prompt(
            base_prompt=base,
            mode=self.config.mode,
            active_app=active_app,
            window_title=window_title,
            selected_text=selected_text,
            context=context,
        )

    def _extract_corrected(self, response_json: dict) -> str | None:
        """Extract corrected text from OpenAI-compatible response. Returns None on malformed."""
        choices = response_json.get("choices", [])
        if not choices:
            return None
        return choices[0].get("message", {}).get("content", "").strip() or None

    def preload(self) -> None:
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

    async def correct_async(
        self,
        text: str,
        language: str | None = None,
        context: list[str] | None = None,
        active_app: str | None = None,
        window_title: str | None = None,
        selected_text: str | None = None,
    ) -> str:
        """Async correction — preferred in server mode to avoid blocking the MLX executor."""
        import httpx

        if not self.config.enabled or not text.strip():
            return text
        if language and language != "tr":
            return text

        messages = build_messages(
            self._build_system_prompt(active_app, window_title, selected_text, context),
            text,
        )

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
                corrected = self._extract_corrected(response.json())

            if not corrected:
                logger.warning("Ollama returned empty output, using original")
                return text
            if len(corrected) > len(text) * 1.5:
                logger.warning("Ollama output too long (%.1fx), using original", len(corrected) / len(text))
                return text

            logger.info("Ollama correction: '%s' -> '%s'", text[:50], corrected[:50])
            return corrected

        except Exception as e:
            logger.error("Ollama async correction failed: %s", e, exc_info=True)
            return text

    def correct(
        self,
        text: str,
        language: str | None = None,
        context: list[str] | None = None,
        active_app: str | None = None,
        window_title: str | None = None,
        selected_text: str | None = None,
    ) -> str:
        """Synchronous correction via Ollama.

        Args:
            text: Raw transcription from Whisper.
            language: Detected language code (only "tr" is corrected).
            context: Optional RAG context chunks.
            window_title: Active window title — untrusted metadata.
            selected_text: Selected text in active app — untrusted metadata.

        Returns:
            Corrected text, or original on failure.
        """
        import httpx

        if not self.config.enabled or not text.strip():
            return text
        if language and language != "tr":
            return text

        messages = build_messages(
            self._build_system_prompt(active_app, window_title, selected_text, context),
            text,
        )

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
            corrected = self._extract_corrected(response.json())

            if not corrected:
                logger.warning("Ollama returned empty output, using original")
                return text
            if len(corrected) > len(text) * 1.5:
                logger.warning("Ollama output too long (%.1fx), using original", len(corrected) / len(text))
                return text

            logger.info("Ollama correction: '%s' -> '%s'", text[:50], corrected[:50])
            return corrected

        except Exception as e:
            logger.error("Ollama correction failed: %s", e, exc_info=True)
            return text
