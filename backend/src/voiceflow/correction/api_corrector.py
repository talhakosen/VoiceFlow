"""Remote LLM correction via any OpenAI-compatible HTTP API.

Works with: Ollama, vLLM, RunPod, mlx-lm server, OpenAI, etc.
Used when BACKEND_MODE=server or LLM_BACKEND=ollama.
"""

import logging
import os
from dataclasses import dataclass, field

from ..core import config as _cfg
from .prompts import (
    BASE_PROMPT, MODE_SUFFIXES, BaseCorrectorConfig,
    build_messages, build_system_prompt, guard_output, pre_process,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPTS = {
    mode: BASE_PROMPT + suffix
    for mode, suffix in MODE_SUFFIXES.items()
}


@dataclass
class APICorrectorConfig(BaseCorrectorConfig):
    """Configuration for the remote API corrector."""

    model_name: str = field(default_factory=lambda: _cfg.LLM_MODEL)
    llm_endpoint: str = field(
        default_factory=lambda: _cfg.LLM_ENDPOINT or "http://localhost:11434"
    )
    api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))


@dataclass
class APICorrector:
    """Corrects transcription text via any OpenAI-compatible HTTP API.

    Compatible endpoints:
    - Ollama:      http://ollama:11434
    - vLLM:        http://vllm:8000
    - mlx-lm:      http://localhost:8080
    - RunPod:      https://<pod>.runpod.net/openai
    """

    config: APICorrectorConfig = field(default_factory=APICorrectorConfig)

    def _build_system_prompt(
        self,
        active_app: str | None,
        window_title: str | None,
        selected_text: str | None,
    ) -> str:
        base = _SYSTEM_PROMPTS.get(self.config.mode, _SYSTEM_PROMPTS["general"])
        return build_system_prompt(
            base_prompt=base,
            mode=self.config.mode,
            active_app=active_app,
            window_title=window_title,
            selected_text=selected_text,
        )

    def _extract_corrected(self, response_json: dict) -> str | None:
        """Extract corrected text from OpenAI-compatible response."""
        choices = response_json.get("choices", [])
        if not choices:
            return None
        return choices[0].get("message", {}).get("content", "").strip() or None

    def _auth_headers(self) -> dict:
        if self.config.api_key:
            return {"Authorization": f"Bearer {self.config.api_key}"}
        return {}

    def preload(self) -> None:
        """Pre-warm the remote model — keeps it resident in GPU memory."""
        import httpx

        try:
            httpx.post(
                f"{self.config.llm_endpoint}/api/generate",
                json={"model": self.config.model_name, "keep_alive": -1},
                timeout=10.0,
            )
            logger.info("API model pre-warmed: %s @ %s", self.config.model_name, self.config.llm_endpoint)
        except Exception as e:
            logger.warning("API pre-warm failed (endpoint may not be ready): %s", e)

    def unload(self) -> None:
        """No-op — remote server manages its own lifecycle."""

    async def correct_async(
        self,
        text: str,
        language: str | None = None,
        active_app: str | None = None,
        window_title: str | None = None,
        selected_text: str | None = None,
    ) -> str:
        """Async correction — preferred in server mode (non-blocking)."""
        import httpx

        if not self.config.enabled or not text.strip():
            return text
        if language and language != "tr":
            return text

        text = pre_process(text)
        if not text.strip():
            return text

        messages = build_messages(
            self._build_system_prompt(active_app, window_title, selected_text),
            text,
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.config.llm_endpoint}/v1/chat/completions",
                    headers=self._auth_headers(),
                    json={
                        "model": self.config.model_name,
                        "messages": messages,
                        "temperature": 0.0,
                        "max_tokens": self.config.max_tokens,
                        "stream": False,
                    },
                )
                response.raise_for_status()

            corrected = guard_output(
                self._extract_corrected(response.json()) or "", text
            )
            if corrected is None:
                return text

            logger.info("API correction: '%s' → '%s'", text[:50], corrected[:50])
            return corrected

        except Exception as e:
            logger.error("API async correction failed: %s", e, exc_info=True)
            return text

    def correct(
        self,
        text: str,
        language: str | None = None,
        active_app: str | None = None,
        window_title: str | None = None,
        selected_text: str | None = None,
    ) -> str:
        """Synchronous correction via remote API."""
        import httpx

        if not self.config.enabled or not text.strip():
            return text
        if language and language != "tr":
            return text

        text = pre_process(text)
        if not text.strip():
            return text

        messages = build_messages(
            self._build_system_prompt(active_app, window_title, selected_text),
            text,
        )

        try:
            response = httpx.post(
                f"{self.config.llm_endpoint}/v1/chat/completions",
                headers=self._auth_headers(),
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

            corrected = guard_output(
                self._extract_corrected(response.json()) or "", text
            )
            if corrected is None:
                return text

            logger.info("API correction: '%s' → '%s'", text[:50], corrected[:50])
            return corrected

        except Exception as e:
            logger.error("API correction failed: %s", e, exc_info=True)
            return text
