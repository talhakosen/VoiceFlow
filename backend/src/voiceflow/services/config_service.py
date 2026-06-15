"""ConfigService — business logic for /api/config endpoint.

Routes delegate here; no HTTP concerns live in this module.
"""

import asyncio
import gc
import logging
import time
from dataclasses import dataclass
from typing import Literal

from ..db import append_audit_log

logger = logging.getLogger(__name__)


@dataclass
class ConfigRequest:
    model: str | None = None
    language: str | None = None
    task: str | None = None
    correction_enabled: bool | None = None
    mode: Literal["general", "engineering", "office"] | None = None
    output_format: Literal["prose", "code_comment", "pr_description", "jira_ticket"] | None = None


@dataclass
class ConfigResult:
    model: str
    language: str
    task: str
    correction_enabled: bool
    mode: str
    output_format: str


async def apply_config(
    config: ConfigRequest,
    svc,
    app_state,
    backend_mode: str,
    user_id: str = "",
    tenant_id: str = "default",
) -> ConfigResult:
    """Apply config changes to RecordingService and return resulting state."""
    from ..transcription import WhisperTranscriber, WhisperConfig
    from ..recording import _mlx_executor

    loop = asyncio.get_running_loop()
    transcriber = svc.transcriber
    corrector = svc.corrector

    # ── Transcriber update ──────────────────────────────────────────
    new_cfg = WhisperConfig(
        model_name=config.model or transcriber.config.model_name,
        language=config.language if config.language is not None else transcriber.config.language,
        task=config.task or transcriber.config.task,
    )
    if (
        new_cfg.model_name != transcriber.config.model_name
        or new_cfg.language != transcriber.config.language
        or new_cfg.task != transcriber.config.task
    ):
        transcriber.unload()
        if backend_mode == "server":
            from ..transcription.faster_whisper import FasterWhisperTranscriber
            svc.update_transcriber(FasterWhisperTranscriber(config=new_cfg))
        else:
            svc.update_transcriber(WhisperTranscriber(config=new_cfg))
        gc.collect()

    # ── Mode update ─────────────────────────────────────────────────
    if config.mode is not None:
        if config.mode == "engineering" and corrector.config.enabled:
            logger.info("Engineering mode: auto-disabling LLM correction")
            corrector.config.update(mode=config.mode, enabled=False)
            if hasattr(corrector, "correct_async"):
                await loop.run_in_executor(None, corrector.unload)
            else:
                await loop.run_in_executor(_mlx_executor, corrector.unload)
        else:
            corrector.config.update(mode=config.mode)

        if config.mode == "engineering":
            await _maybe_reindex(app_state, user_id)

    # ── Output format ───────────────────────────────────────────────
    if config.output_format is not None:
        corrector.config.update(output_format=config.output_format)

    # ── Correction enable/disable ───────────────────────────────────
    if config.correction_enabled is not None:
        was_enabled = corrector.config.enabled
        corrector.config.update(enabled=config.correction_enabled)

        if config.correction_enabled and not was_enabled:
            logger.info("Correction enabled, loading LLM model...")
            if hasattr(corrector, "correct_async"):
                await loop.run_in_executor(None, corrector.preload)
            else:
                # Loading the local MLX LLM re-cools whisper's compiled Metal
                # state. Re-warm whisper in the SAME executor task so this runs
                # atomically before any dictation the user starts meanwhile —
                # otherwise a transcribe enqueued during the load races ahead of
                # a separate re-warm task and pays the full cold cost.
                transcriber = svc.transcriber

                def _load_llm_then_rewarm() -> None:
                    corrector.preload()
                    _warm = getattr(transcriber, "warm", None)
                    if _warm is not None:
                        _warm()

                await loop.run_in_executor(_mlx_executor, _load_llm_then_rewarm)
        elif not config.correction_enabled and was_enabled:
            logger.info("Correction disabled, unloading LLM model...")
            if hasattr(corrector, "correct_async"):
                await loop.run_in_executor(None, corrector.unload)
            else:
                await loop.run_in_executor(_mlx_executor, corrector.unload)

    # ── Audit log ───────────────────────────────────────────────────
    changed = {k: v for k, v in vars(config).items() if v is not None}
    if changed:
        await append_audit_log(
            tenant_id=tenant_id,
            action="config_changed",
            user_id=user_id,
            target=str(changed),
        )

    return ConfigResult(
        model=svc.transcriber.config.model_name,
        language=svc.transcriber.config.language,
        task=svc.transcriber.config.task,
        correction_enabled=corrector.config.enabled,
        mode=corrector.config.mode,
        output_format=getattr(corrector.config, "output_format", "prose"),
    )


async def _maybe_reindex(app_state, user_id: str) -> None:
    """Trigger symbol re-index if last index is stale (>5 min)."""
    last_paths = getattr(app_state, "last_index_paths", {})
    entry = last_paths.get(user_id) or last_paths.get("default")
    if not entry or (time.time() - entry["indexed_at"]) <= 300:
        return

    async def _reindex(path: str, uid: str) -> None:
        try:
            from ..symbol import build_symbol_index, generate_project_notes
            sym_count = await build_symbol_index(path, uid)
            logger.info("Auto re-index (engineering mode): %d symbols", sym_count)
            if sym_count > 0:
                await generate_project_notes(path, uid)
            if not hasattr(app_state, "last_index_paths"):
                app_state.last_index_paths = {}
            app_state.last_index_paths[uid] = {"path": path, "indexed_at": time.time()}
        except Exception as exc:
            logger.warning("Auto re-index failed: %s", exc)

    asyncio.create_task(_reindex(entry["path"], user_id))
