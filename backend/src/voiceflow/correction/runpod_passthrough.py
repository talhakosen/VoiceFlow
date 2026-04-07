"""No-op corrector for RunPod mode.

When WHISPER_BACKEND=runpod, the serverless handler already performs
LLM correction. This corrector reads the cached result from
RunPodTranscriber instead of running correction again.
"""

import logging

from ..core.interfaces import AbstractCorrector
from .prompts import BaseCorrectorConfig

logger = logging.getLogger(__name__)


class RunPodPassthroughCorrector(AbstractCorrector):
    """Returns the corrected text that RunPod already computed.

    RecordingService holds a reference to the transcriber. After
    RunPodTranscriber.transcribe() runs, it caches the corrected text.
    This corrector retrieves that cached result.
    """

    def __init__(self):
        self.config = BaseCorrectorConfig(enabled=True)
        self._transcriber_ref = None

    def set_transcriber(self, transcriber) -> None:
        """Link to the RunPodTranscriber to read cached correction results."""
        self._transcriber_ref = transcriber
        self._sync_enabled()

    def _sync_enabled(self) -> None:
        """Sync correction enabled state to the transcriber."""
        if self._transcriber_ref and hasattr(self._transcriber_ref, "_correction_enabled"):
            self._transcriber_ref._correction_enabled = self.config.enabled

    def preload(self) -> None:
        self._sync_enabled()
        logger.info("RunPodPassthroughCorrector: no-op preload (correction runs on RunPod)")

    def unload(self) -> None:
        self._sync_enabled()

    def correct(
        self,
        text: str,
        language: str | None = None,
        context: list[str] | None = None,
        active_app: str | None = None,
        **kwargs,
    ) -> str:
        """Return RunPod's already-corrected text."""
        if self._transcriber_ref and hasattr(self._transcriber_ref, "last_corrected_text"):
            corrected = self._transcriber_ref.last_corrected_text
            if corrected:
                return corrected
        return text

    async def correct_async(
        self,
        text: str,
        language: str | None = None,
        context: list[str] | None = None,
        active_app: str | None = None,
        **kwargs,
    ) -> str:
        """Async version — same passthrough logic."""
        return self.correct(text, language, context, active_app, **kwargs)
