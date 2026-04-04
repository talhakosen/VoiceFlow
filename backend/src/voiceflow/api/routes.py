"""FastAPI routes — HTTP layer only.

Each handler: validate input → call RecordingService → return response.
No business logic here.
"""

import asyncio
import gc
import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from .auth import verify_api_key
from ..db import (
    get_history, clear_history,
    get_dictionary, add_dictionary_entry, delete_dictionary_entry,
    get_snippets, add_snippet, delete_snippet,
    append_audit_log, save_feedback,
    import_training_sentences, get_random_unrecorded_sentence, get_training_sentence_by_id,
    save_training_recording, delete_training_recording, get_recordings_for_sentence,
    get_recorded_sentences,
)

from ..core.config import BACKEND_MODE as _BACKEND_MODE
logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_api_key)])


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

class StatusResponse(BaseModel):
    status: str
    is_recording: bool


class TranscriptionResponse(BaseModel):
    text: str
    raw_text: str | None = None
    corrected: bool = False
    snippet_used: bool = False
    language: str | None = None
    duration: float | None = None
    processing_ms: int | None = None
    id: int | None = None
    it_wav_path: str | None = None
    pending_wav_path: str | None = None
    symbol_refs: list[str] | None = None


class ConfigRequest(BaseModel):
    model: str | None = None
    language: str | None = None
    task: str | None = None          # "transcribe" | "translate"
    correction_enabled: bool | None = None
    mode: str | None = None          # "general" | "engineering" | "office"
    output_format: str | None = None  # "prose" | "code_comment" | "pr_description" | "jira_ticket"


# ------------------------------------------------------------------
# Dependency: RecordingService from app.state
# ------------------------------------------------------------------

def get_service(request: Request):
    return request.app.state.recording_service


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.get("/status", response_model=StatusResponse)
async def get_status(svc=Depends(get_service)):
    return StatusResponse(status=svc.state, is_recording=svc.is_recording)


@router.post("/start", response_model=StatusResponse)
async def start_recording(svc=Depends(get_service)):
    try:
        svc.start()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return StatusResponse(status=svc.state, is_recording=svc.is_recording)


@router.post("/stop", response_model=TranscriptionResponse)
async def stop_recording(
    request: Request,
    svc=Depends(get_service),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    x_active_app: str | None = Header(default=None, alias="X-Active-App"),
    x_window_title: str | None = Header(default=None, alias="X-Window-Title"),
    x_selected_text: str | None = Header(default=None, alias="X-Selected-Text"),
    x_cmd_intervals: str | None = Header(default=None, alias="X-Cmd-Intervals"),
    x_it_dataset_index: str | None = Header(default=None, alias="X-IT-Dataset-Index"),
    x_training_mode: str | None = Header(default=None, alias="X-Training-Mode"),
):
    # JWT sets request.state; fall back to X-User-ID header for local mode compat
    state_user_id = getattr(request.state, "user_id", None)
    user_id = state_user_id or x_user_id or None
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"

    # Parse "1.10-2.30,4.50-5.10" → [(1.10, 2.30), (4.50, 5.10)]
    cmd_intervals: list[tuple[float, float]] | None = None
    if x_cmd_intervals:
        try:
            cmd_intervals = [
                (float(a), float(b))
                for part in x_cmd_intervals.split(",")
                for a, b in [part.strip().split("-", 1)]
            ]
        except Exception:
            cmd_intervals = None

    # Parse IT dataset index
    it_dataset_idx: int | None = None
    if x_it_dataset_index:
        try:
            it_dataset_idx = int(x_it_dataset_index)
        except ValueError:
            it_dataset_idx = None

    save_pending_wav = x_training_mode == "1" and it_dataset_idx is None

    try:
        result = await svc.stop(
            user_id=user_id,
            tenant_id=tenant_id,
            active_app=x_active_app or None,
            window_title=x_window_title or None,
            selected_text=x_selected_text or None,
            cmd_intervals=cmd_intervals,
            it_dataset_index=it_dataset_idx,
            save_pending_wav=save_pending_wav,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return TranscriptionResponse(**result)


@router.post("/force-stop")
async def force_stop(svc=Depends(get_service)):
    was_recording = svc.force_stop()
    return {"status": "stopped", "was_recording": was_recording}


@router.get("/devices")
async def get_devices(svc=Depends(get_service)):
    return {"devices": svc.get_devices()}


@router.post("/config")
async def update_config(config: ConfigRequest, request: Request, svc=Depends(get_service)):
    from ..transcription import WhisperTranscriber, WhisperConfig

    loop = asyncio.get_running_loop()

    transcriber = svc.transcriber
    corrector = svc.corrector

    # Update transcriber if config changed
    new_cfg = WhisperConfig(
        model_name=config.model or transcriber.config.model_name,
        language=config.language if config.language is not None else transcriber.config.language,
        task=config.task or transcriber.config.task,
    )
    if (new_cfg.model_name != transcriber.config.model_name
            or new_cfg.language != transcriber.config.language
            or new_cfg.task != transcriber.config.task):
        transcriber.unload()
        if _BACKEND_MODE == "server":
            from ..transcription.faster_whisper import FasterWhisperTranscriber
            svc.update_transcriber(FasterWhisperTranscriber(config=new_cfg))
        else:
            svc.update_transcriber(WhisperTranscriber(config=new_cfg))
        gc.collect()

    # Update mode — engineering mode auto-disables LLM correction
    if config.mode is not None:
        corrector.config.mode = config.mode
        if config.mode == "engineering" and corrector.config.enabled:
            logger.info("Engineering mode: auto-disabling LLM correction")
            corrector.config.enabled = False
            from ..services.recording import _mlx_executor
            if hasattr(corrector, "correct_async"):
                await loop.run_in_executor(None, corrector.unload)
            else:
                await loop.run_in_executor(_mlx_executor, corrector.unload)

        if config.mode == "engineering":
            # Auto re-index if last path is known and index is stale (>5 min)
            import time as _time
            last_paths = getattr(request.app.state, "last_index_paths", {})
            req_user_id = getattr(request.state, "user_id", "") or ""
            entry = last_paths.get(req_user_id) or last_paths.get("default")
            if entry and (_time.time() - entry["indexed_at"]) > 300:
                async def _reindex(path: str, uid: str, app_state) -> None:
                    try:
                        from ..services.symbol_indexer import build_symbol_index, generate_project_notes
                        sym_count = await build_symbol_index(path, uid)
                        logger.info("Auto re-index (engineering mode): %d symbols", sym_count)
                        if sym_count > 0:
                            await generate_project_notes(path, uid)
                        import time as _t
                        if not hasattr(app_state, "last_index_paths"):
                            app_state.last_index_paths = {}
                        app_state.last_index_paths[uid] = {"path": path, "indexed_at": _t.time()}
                    except Exception as _e:
                        logger.warning("Auto re-index failed: %s", _e)
                asyncio.create_task(_reindex(entry["path"], req_user_id, request.app.state))

    # Update output format
    if config.output_format is not None:
        valid_formats = {"prose", "code_comment", "pr_description", "jira_ticket"}
        if config.output_format not in valid_formats:
            raise HTTPException(status_code=400, detail=f"output_format must be one of {sorted(valid_formats)}")
        corrector.config.output_format = config.output_format

    # Update correction enabled/disabled
    if config.correction_enabled is not None:
        was_enabled = corrector.config.enabled
        corrector.config.enabled = config.correction_enabled

        from ..services.recording import _mlx_executor
        if config.correction_enabled and not was_enabled:
            logger.info("Correction enabled, loading LLM model...")
            if hasattr(corrector, "correct_async"):
                await loop.run_in_executor(None, corrector._ensure_model_loaded)
            else:
                await loop.run_in_executor(_mlx_executor, corrector._ensure_model_loaded)
        elif not config.correction_enabled and was_enabled:
            logger.info("Correction disabled, unloading LLM model...")
            if hasattr(corrector, "correct_async"):
                await loop.run_in_executor(None, corrector.unload)
            else:
                await loop.run_in_executor(_mlx_executor, corrector.unload)

    result = {
        "model": svc.transcriber.config.model_name,
        "language": svc.transcriber.config.language,
        "task": svc.transcriber.config.task,
        "correction_enabled": corrector.config.enabled,
        "mode": corrector.config.mode,
        "output_format": getattr(corrector.config, "output_format", "prose"),
    }
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"
    user_id = getattr(request.state, "user_id", "") or ""
    await append_audit_log(
        tenant_id=tenant_id,
        action="config_changed",
        user_id=user_id,
        target=str({k: v for k, v in config.model_dump().items() if v is not None}),
    )
    return result


@router.get("/history")
async def history(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    user_id: str | None = None,
):
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"
    rows = await get_history(limit=limit, offset=offset, user_id=user_id, tenant_id=tenant_id)
    return {"items": rows, "count": len(rows)}


@router.delete("/history")
async def delete_history(request: Request):
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"
    user_id = getattr(request.state, "user_id", "") or ""
    await clear_history()
    await append_audit_log(tenant_id=tenant_id, action="history_cleared", user_id=user_id)
    return {"status": "cleared"}


# ------------------------------------------------------------------
# Context Engine (Phase 2)
# ------------------------------------------------------------------

class IngestRequest(BaseModel):
    path: str


@router.post("/context/ingest")
async def context_ingest(
    body: IngestRequest,
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """Scan folder, extract identifiers, populate smart dictionary."""
    from ..services.smart_dictionary import build_smart_dictionary

    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"

    async def _run():
        try:
            added = await build_smart_dictionary(body.path, user_id)
            logger.info("Smart dictionary: %d entries added for user %s", added, user_id)
        except Exception as e:
            logger.warning("Smart dictionary failed: %s", e)
        try:
            from ..services.symbol_indexer import build_symbol_index, generate_project_notes
            sym_count = await build_symbol_index(body.path, user_id)
            logger.info("Symbol index: %d symbols for user %s", sym_count, user_id)
            if sym_count > 0:
                notes_path = await generate_project_notes(body.path, user_id)
                if notes_path:
                    logger.info("Project notes generated: %s", notes_path)
        except Exception as e:
            logger.warning("Symbol index failed: %s", e)

    import time as _t
    if not hasattr(request.app.state, "last_index_paths"):
        request.app.state.last_index_paths = {}
    request.app.state.last_index_paths[user_id] = {"path": body.path, "indexed_at": _t.time()}

    task = asyncio.create_task(_run())
    request.app.state.ingest_task = task
    return {"status": "started", "path": body.path, "message": "Smart dictionary scan in background"}


@router.get("/context/status")
async def context_status(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    request: Request = None,
):
    """Return smart dictionary + symbol index status."""
    import aiosqlite
    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"
    from ..db.storage import DB_PATH as db_path
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM user_dictionary WHERE user_id = ? AND scope = 'smart'",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            n = row[0] if row else 0
        async with db.execute(
            "SELECT COUNT(*), MAX(indexed_at) FROM symbol_index_v2 WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row2 = await cursor.fetchone()
            sym_count = row2[0] if row2 else 0
            last_indexed_at = row2[1] if row2 else None

    last_paths = getattr(request.app.state, "last_index_paths", {}) if request else {}
    entry = last_paths.get(user_id) or last_paths.get("default")
    return {
        "count": n,
        "is_ready": True,
        "is_empty": n == 0,
        "symbol_count": sym_count,
        "last_indexed_at": last_indexed_at,
        "last_index_path": entry["path"] if entry else None,
    }


@router.get("/context/projects")
async def context_projects(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    request: Request = None,
):
    """Return indexed projects with smart dictionary + symbol counts."""
    import aiosqlite
    from pathlib import Path
    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"
    from ..db.storage import DB_PATH as db_path
    async with aiosqlite.connect(db_path) as db:
        # Symbol counts per project
        async with db.execute(
            "SELECT project_path, COUNT(*) FROM symbol_index WHERE user_id = ? GROUP BY project_path",
            (user_id,),
        ) as cursor:
            symbol_rows = {row[0]: row[1] for row in await cursor.fetchall()}

        # Smart dictionary total (all belong to latest ingest — no per-project tracking yet)
        async with db.execute(
            "SELECT COUNT(*) FROM user_dictionary WHERE user_id = ? AND scope = 'smart'",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            smart_total = row[0] if row else 0

    projects = []
    for path, sym_count in symbol_rows.items():
        projects.append({
            "path": path,
            "name": Path(path).name,
            "symbol_count": sym_count,
        })

    return {
        "projects": projects,
        "smart_word_count": smart_total,
        "total_symbols": sum(p["symbol_count"] for p in projects),
    }


@router.get("/symbol/lookup")
async def symbol_lookup(
    q: str,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    request: Request = None,
    limit: int = 5,
):
    """Fuzzy symbol lookup. Returns file_path:line_number matches."""
    from ..services.symbol_indexer import lookup_symbol
    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"
    results = await lookup_symbol(query=q, user_id=user_id, limit=limit)
    return {"query": q, "results": results}


@router.delete("/context")
async def context_clear(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
    request: Request = None,
):
    """Clear smart dictionary entries for this user."""
    import aiosqlite
    from pathlib import Path
    user_id = x_user_id or getattr(request.state, "user_id", None) or "default"
    from ..db.storage import DB_PATH as db_path
    async with aiosqlite.connect(db_path) as db:
        await db.execute("DELETE FROM user_dictionary WHERE user_id = ?", (user_id,))
        await db.commit()
    return {"status": "cleared"}


# ------------------------------------------------------------------
# Dictionary (Katman 1)
# ------------------------------------------------------------------

class DictionaryEntryRequest(BaseModel):
    trigger: str
    replacement: str
    scope: str = "personal"


@router.get("/dictionary")
async def get_dict(x_user_id: str | None = Header(default=None, alias="X-User-ID")):
    user_id = x_user_id or ""
    entries = await get_dictionary(user_id=user_id)
    return {"items": entries, "count": len(entries)}


@router.post("/dictionary")
async def add_dict_entry(
    body: DictionaryEntryRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    if not body.trigger.strip() or not body.replacement.strip():
        raise HTTPException(status_code=400, detail="trigger and replacement must not be empty")
    if body.scope not in ("personal", "team"):
        raise HTTPException(status_code=400, detail="scope must be 'personal' or 'team'")
    user_id = x_user_id or ""
    entry_id = await add_dictionary_entry(
        trigger=body.trigger,
        replacement=body.replacement,
        user_id=user_id,
        scope=body.scope,
    )
    return {"id": entry_id, "trigger": body.trigger, "replacement": body.replacement, "scope": body.scope}


@router.post("/dictionary/bundle")
async def load_dict_bundle(x_user_id: str | None = Header(default=None, alias="X-User-ID")):
    """Load the pre-built IT Turkish phonetics bundle into DB (scope=bundle, hidden from UI)."""
    import json as _json
    from pathlib import Path
    bundle_path = Path(__file__).parents[4] / "ml" / "dictionary" / "it_bundle_full.json"
    if not bundle_path.exists():
        raise HTTPException(status_code=404, detail="Bundle file not found")
    with open(bundle_path, encoding="utf-8") as f:
        entries = _json.load(f)
    import aiosqlite
    from ..db.storage import DB_PATH as _db_path
    async with aiosqlite.connect(_db_path) as db:
        # Clear existing bundle entries for this tenant first
        await db.execute("DELETE FROM user_dictionary WHERE tenant_id = ? AND scope = 'bundle'", ("default",))
        await db.executemany(
            "INSERT OR IGNORE INTO user_dictionary (tenant_id, user_id, trigger, replacement, scope) VALUES (?, ?, ?, ?, 'bundle')",
            [("default", "", e["trigger"], e["replacement"]) for e in entries],
        )
        await db.commit()
    return {"status": "loaded", "count": len(entries)}


@router.delete("/dictionary/bundle")
async def clear_dict_bundle():
    """Remove all bundle entries."""
    import aiosqlite
    from ..db.storage import DB_PATH as _db_path
    async with aiosqlite.connect(_db_path) as db:
        await db.execute("DELETE FROM user_dictionary WHERE scope = 'bundle'")
        await db.commit()
    return {"status": "cleared"}


@router.delete("/dictionary/{entry_id}")
async def delete_dict_entry(
    entry_id: int,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    user_id = x_user_id or ""
    deleted = await delete_dictionary_entry(entry_id=entry_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entry not found or not yours")
    return {"status": "deleted", "id": entry_id}


# ------------------------------------------------------------------
# Snippets (Katman 1)
# ------------------------------------------------------------------

class SnippetRequest(BaseModel):
    trigger_phrase: str
    expansion: str
    scope: str = "personal"


@router.get("/snippets")
async def get_snippets_route(x_user_id: str | None = Header(default=None, alias="X-User-ID")):
    user_id = x_user_id or ""
    items = await get_snippets(user_id=user_id)
    return {"items": items, "count": len(items)}


@router.post("/snippets")
async def add_snippet_route(
    body: SnippetRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    if not body.trigger_phrase.strip() or not body.expansion.strip():
        raise HTTPException(status_code=400, detail="trigger_phrase and expansion must not be empty")
    if body.scope not in ("personal", "team"):
        raise HTTPException(status_code=400, detail="scope must be 'personal' or 'team'")
    user_id = x_user_id or ""
    snippet_id = await add_snippet(
        trigger_phrase=body.trigger_phrase,
        expansion=body.expansion,
        user_id=user_id,
        scope=body.scope,
    )
    return {"id": snippet_id, "trigger_phrase": body.trigger_phrase, "expansion": body.expansion, "scope": body.scope}


@router.delete("/snippets/{snippet_id}")
async def delete_snippet_route(
    snippet_id: int,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    user_id = x_user_id or ""
    deleted = await delete_snippet(snippet_id=snippet_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Snippet not found or not yours")
    return {"status": "deleted", "id": snippet_id}


# ------------------------------------------------------------------
# Training Mode — Feedback (Katman 4)
# ------------------------------------------------------------------

_VALID_ACTIONS = {"approved", "edited", "dismissed"}


class FeedbackRequest(BaseModel):
    raw_whisper: str
    model_output: str
    user_action: str   # 'approved' | 'edited' | 'dismissed'
    user_edit: str | None = None
    app_context: str | None = None
    window_title: str | None = None
    mode: str | None = None
    language: str | None = None


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest, request: Request):
    if req.user_action not in _VALID_ACTIONS:
        raise HTTPException(status_code=400, detail=f"user_action must be one of {sorted(_VALID_ACTIONS)}")
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", "default") or "default"
    await save_feedback(
        raw_whisper=req.raw_whisper,
        model_output=req.model_output,
        user_action=req.user_action,
        tenant_id=tenant_id,
        user_id=user_id,
        user_edit=req.user_edit,
        app_context=req.app_context,
        window_title=req.window_title,
        mode=req.mode,
        language=req.language,
    )
    return {"status": "ok"}

# ------------------------------------------------------------------
# IT Dataset Recording (Engineering Whisper training)
# ------------------------------------------------------------------

_IT_DATASET_PATH = Path(__file__).parents[4] / "ml" / "whisper" / "datasets" / "it_dataset" / "whisper_sentences.jsonl"
_IT_TERMS_PATH   = Path(__file__).parents[4] / "ml" / "whisper" / "datasets" / "it_dataset" / "it_terms.jsonl"
_IT_RECORDINGS_DIR = Path(__file__).parents[4] / "ml" / "whisper" / "datasets" / "it_dataset" / "recordings"
_USER_CORRECTIONS_DIR = Path(__file__).parents[4] / "ml" / "whisper" / "datasets" / "user_corrections"
_USER_CORRECTIONS_JSONL = _USER_CORRECTIONS_DIR / "corrections.jsonl"

_TRAINING_DATA_PATHS: dict[str, Path] = {
    "it_dataset": _IT_DATASET_PATH,
    "it_terms":   _IT_TERMS_PATH,
}


class ITRecording(BaseModel):
    whisper: str
    wav_path: str


class ITDatasetResponse(BaseModel):
    index: int          # sentence_id in DB
    total: int
    sentence: str
    persona: str | None = None
    scenario: str | None = None
    recordings: list[ITRecording] = []


class ITRecordRequest(BaseModel):
    index: int          # sentence_id in DB
    whisper_output: str
    audio_b64: str | None = None


class ITDeleteRequest(BaseModel):
    wav_path: str


async def _ensure_sentences_imported(training_set: str = "it_dataset") -> None:
    """Import sentences from JSONL on first run (idempotent — skips if already imported)."""
    data_path = _TRAINING_DATA_PATHS.get(training_set, _IT_DATASET_PATH)
    if not data_path.exists():
        return
    with open(data_path) as f:
        sentences = [json.loads(l) for l in f if l.strip()]
    if not sentences:
        return
    n = await import_training_sentences(training_set, sentences)
    if n > 0:
        logger.info("Imported %d training sentences for '%s'", n, training_set)


@router.get("/it-dataset/next")
async def get_next_it_sentence(offset: int = 0, training_set: str = "it_dataset") -> ITDatasetResponse:
    """Return a random unrecorded sentence. `offset` param kept for backwards compat (ignored)."""
    await _ensure_sentences_imported(training_set)
    row = await get_random_unrecorded_sentence(training_set)
    if row is None:
        return ITDatasetResponse(index=-1, total=0, sentence="")
    recs = await get_recordings_for_sentence(row["id"])
    return ITDatasetResponse(
        index=row["id"],
        total=row["total"],
        sentence=row["text"],
        persona=row["persona"],
        scenario=row["scenario"],
        recordings=[ITRecording(whisper=r["whisper_out"] or "", wav_path=r["wav_path"]) for r in recs],
    )


@router.get("/it-dataset/random")
async def get_random_it_sentence(training_set: str = "it_dataset") -> ITDatasetResponse:
    """Shuffle — return a different random unrecorded sentence."""
    await _ensure_sentences_imported(training_set)
    row = await get_random_unrecorded_sentence(training_set)
    if row is None:
        return ITDatasetResponse(index=-1, total=0, sentence="")
    recs = await get_recordings_for_sentence(row["id"])
    return ITDatasetResponse(
        index=row["id"],
        total=row["total"],
        sentence=row["text"],
        persona=row["persona"],
        scenario=row["scenario"],
        recordings=[ITRecording(whisper=r["whisper_out"] or "", wav_path=r["wav_path"]) for r in recs],
    )


@router.post("/it-dataset/record")
async def record_it_pair(req: ITRecordRequest, request: Request) -> dict:
    sentence = await get_training_sentence_by_id(req.index)
    if sentence is None:
        raise HTTPException(status_code=400, detail="Invalid sentence id")

    # Save audio
    wav_path_str = ""
    import base64
    import time
    if req.audio_b64:
        _IT_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        audio_bytes = base64.b64decode(req.audio_b64)
        ts = int(time.time() * 1000)
        wav_path = _IT_RECORDINGS_DIR / f"{req.index:05d}_{ts}.wav"
        wav_path.write_bytes(audio_bytes)
        wav_path_str = str(wav_path)

    await save_training_recording(
        sentence_id=req.index,
        training_set=sentence["training_set"],
        wav_path=wav_path_str,
        whisper_out=req.whisper_output,
    )
    logger.info("IT recording saved: sentence_id=%d whisper='%s'", req.index, req.whisper_output[:60])
    return {"status": "ok"}


@router.delete("/it-dataset/record")
async def delete_it_pair(req: ITDeleteRequest) -> dict:
    wav = Path(req.wav_path)
    if wav.exists():
        wav.unlink()
        logger.info("IT WAV deleted: %s", wav)
    await delete_training_recording(req.wav_path)
    return {"status": "ok"}


@router.get("/it-dataset/recorded")
async def get_recorded_it_sentences(training_set: str = "it_dataset") -> list[ITDatasetResponse]:
    """All sentences with at least one recording (Pratik tab)."""
    rows = await get_recorded_sentences(training_set)
    return [
        ITDatasetResponse(
            index=r["id"],
            total=r["total"],
            sentence=r["text"],
            persona=r["persona"],
            scenario=r["scenario"],
            recordings=[ITRecording(**rec) for rec in r["recordings"]],
        )
        for r in rows
    ]


# ------------------------------------------------------------------
# User correction training pairs
# ------------------------------------------------------------------

class SaveCorrectionRequest(BaseModel):
    wav_path: str
    whisper_text: str
    corrected_text: str


class DeletePendingWavRequest(BaseModel):
    wav_path: str


@router.post("/training/save-correction")
async def save_user_correction(req: SaveCorrectionRequest) -> dict:
    """Keep pending WAV and append (wav, whisper, corrected) pair to JSONL."""
    wav = Path(req.wav_path)
    if not wav.exists():
        raise HTTPException(status_code=404, detail="WAV not found")

    # Move from pending/ to user_corrections/
    final_dir = _USER_CORRECTIONS_DIR
    final_dir.mkdir(parents=True, exist_ok=True)
    final_path = final_dir / wav.name
    wav.rename(final_path)

    # Append to JSONL
    import json as _json
    with open(_USER_CORRECTIONS_JSONL, "a", encoding="utf-8") as f:
        f.write(_json.dumps({
            "audio": str(final_path),
            "whisper_out": req.whisper_text,
            "corrected": req.corrected_text,
        }, ensure_ascii=False) + "\n")

    logger.info("User correction saved: %s → '%s'", final_path.name, req.corrected_text[:60])
    return {"status": "ok", "wav_path": str(final_path)}


@router.delete("/training/pending-wav")
async def delete_pending_wav(req: DeletePendingWavRequest) -> dict:
    """Delete a pending WAV (user dismissed or approved without editing)."""
    wav = Path(req.wav_path)
    if wav.exists():
        wav.unlink()
        logger.info("Pending WAV deleted: %s", wav.name)
    return {"status": "ok"}
