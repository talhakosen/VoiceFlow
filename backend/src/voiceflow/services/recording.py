"""RecordingService — orchestrates audio capture, transcription, and correction.

Single responsibility: coordinate the start→stop→transcribe→correct→persist pipeline.
Routes delegate to this service; they only handle HTTP concerns.
"""

import asyncio
import functools
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from ..audio import AudioCapture, AudioConfig
from ..core.interfaces import AbstractCorrector, AbstractTranscriber, TranscriptionResult
from ..db import save_transcription, get_dictionary, get_snippets
from ..services.dictionary import _apply_aho_corasick, _apply_regex_fallback, _build_automaton, _HAS_AC
from ..services.snippets import apply_snippets
from ..services.filler_cleaner import clean_fillers

logger = logging.getLogger(__name__)

# Single-thread executor for MLX operations (Metal GPU is not thread-safe)
_mlx_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mlx")


_SAMPLE_RATE = 16000
_MIN_CHUNK_SECONDS = 0.3  # daha kısa parçaları atla (gürültü)


async def _transcribe_segmented(
    audio_data,
    cmd_intervals: list[tuple[float, float]],
    transcriber: "AbstractTranscriber",
    user_id: str,
    loop,
) -> tuple[str, str | None, float]:
    """Sesi cmd aralıklarına göre böl, her parçayı ayrı transcribe et.

    Cmd-held parçalar → transcribe → inject_symbol_refs
    Normal parçalar   → transcribe → olduğu gibi bırak

    word_timestamps kullanılmaz — Whisper'a ekstra yük yok.

    Returns: (merged_text, language, total_duration_seconds)
    """
    from .symbol_indexer import inject_symbol_refs

    total_samples = len(audio_data)
    total_duration = total_samples / _SAMPLE_RATE

    # Tüm segmentleri (start, end, is_cmd) olarak listele
    segments: list[tuple[float, float, bool]] = []
    prev = 0.0
    for s, e in sorted(cmd_intervals):
        s = max(0.0, min(s, total_duration))
        e = max(0.0, min(e, total_duration))
        if s > prev + _MIN_CHUNK_SECONDS:
            segments.append((prev, s, False))
        if e > s + _MIN_CHUNK_SECONDS:
            segments.append((s, e, True))
        prev = e
    if prev + _MIN_CHUNK_SECONDS < total_duration:
        segments.append((prev, total_duration, False))

    parts: list[str] = []
    detected_language: str | None = None

    for start, end, is_cmd in segments:
        chunk = audio_data[int(start * _SAMPLE_RATE): int(end * _SAMPLE_RATE)]
        if len(chunk) < int(_MIN_CHUNK_SECONDS * _SAMPLE_RATE):
            continue
        seg_result = await loop.run_in_executor(_mlx_executor, transcriber.transcribe, chunk)
        if not seg_result.text.strip():
            continue
        if detected_language is None and seg_result.language:
            detected_language = seg_result.language
        text = seg_result.text.strip()
        if is_cmd and user_id:
            text = await inject_symbol_refs(text, user_id)
            logger.info("Cmd segment injected: '%s'", text[:80])
        parts.append(text)

    return " ".join(parts), detected_language, total_duration


class RecordingService:
    """Coordinates the full voice recording pipeline.

    Injected with concrete transcriber and corrector implementations —
    swap out for mocks in tests or for different backend modes.
    """

    def __init__(
        self,
        transcriber: AbstractTranscriber,
        corrector: AbstractCorrector,
    ) -> None:
        self._audio = AudioCapture(config=AudioConfig())
        self._transcriber = transcriber
        self._corrector = corrector
        # Aho-Corasick automaton cache: rebuilt only when dictionary entries change
        self._dict_automaton: object | None = None
        self._dict_entry_count: int = 0

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @property
    def is_recording(self) -> bool:
        return self._audio.is_recording

    @property
    def state(self) -> str:
        return self._audio.state.value

    def get_devices(self) -> list:
        return self._audio.get_devices()

    # ------------------------------------------------------------------
    # Recording lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start audio capture. Raises ValueError if already recording."""
        if self._audio.is_recording:
            raise ValueError("Already recording")
        self._audio.start()

    async def stop(
        self,
        user_id: str | None = None,
        tenant_id: str = "default",
        active_app: str | None = None,
        window_title: str | None = None,
        selected_text: str | None = None,
        cmd_intervals: list[tuple[float, float]] | None = None,
        it_dataset_index: int | None = None,
        save_pending_wav: bool = False,
    ) -> dict:
        """Stop recording, transcribe, optionally correct, persist to DB.

        Returns a dict ready for the API response.
        """
        if not self._audio.is_recording:
            raise ValueError("Not recording")

        t_start = time.perf_counter()
        audio_data = self._audio.stop()
        logger.info("Audio capture stop: %.3fs, samples: %d", time.perf_counter() - t_start, len(audio_data))

        if len(audio_data) == 0:
            return {"text": "", "duration": 0.0}

        loop = asyncio.get_running_loop()

        t_whisper = time.perf_counter()
        if cmd_intervals:
            # Sesi böl: cmd parçaları ayrı transcribe → inject, diğerleri düz
            merged_text, language, duration = await _transcribe_segmented(
                audio_data, cmd_intervals, self._transcriber, user_id, loop
            )
            result = TranscriptionResult(text=merged_text, language=language, duration=duration)
        else:
            result = await loop.run_in_executor(_mlx_executor, self._transcriber.transcribe, audio_data)
        logger.info("Whisper: %.3fs → '%s'", time.perf_counter() - t_whisper, result.text[:80])

        raw_text = result.text

        # IT Dataset: save WAV + recording to SQLite
        _it_wav_path: str | None = None
        if it_dataset_index is not None and len(audio_data) > 0:
            try:
                import soundfile as sf
                from pathlib import Path as _Path
                import time as _t
                from ..db import get_training_sentence_by_id, save_training_recording
                wav_dir = _Path(__file__).parents[4] / "ml" / "whisper" / "datasets" / "it_dataset" / "recordings"
                wav_dir.mkdir(parents=True, exist_ok=True)
                ts = int(_t.time() * 1000)
                wav_path = wav_dir / f"{it_dataset_index:05d}_{ts}.wav"
                sf.write(str(wav_path), audio_data, _SAMPLE_RATE)
                _it_wav_path = str(wav_path)
                logger.info("IT dataset WAV saved: %s", wav_path)

                if not raw_text.strip():
                    # Boş veya hallüsinasyon sonrası temizlenmiş — kaydetme
                    wav_path.unlink(missing_ok=True)
                    _it_wav_path = None
                    logger.warning("IT recording skipped: empty/hallucination text for sentence_id=%d", it_dataset_index)
                else:
                    sentence = await get_training_sentence_by_id(it_dataset_index)
                    training_set = sentence["training_set"] if sentence else "it_dataset"
                    await save_training_recording(
                        sentence_id=it_dataset_index,
                        training_set=training_set,
                        wav_path=str(wav_path),
                        whisper_out=raw_text,
                    )
                    logger.info("IT recording saved: id=%d whisper='%s'", it_dataset_index, raw_text[:60])
            except Exception as e:
                logger.warning("IT dataset save failed: %s", e)
        active_mode = self._corrector.config.mode  # capture before concurrent /config can mutate

        # IT Dataset mode: skip all post-processing, return raw Whisper output
        if it_dataset_index is not None:
            processing_ms = int((time.perf_counter() - t_start) * 1000)
            row_id = await save_transcription(
                text=raw_text, raw_text=None, corrected=False,
                language=result.language, duration=result.duration,
                mode=active_mode, user_id=user_id, tenant_id=tenant_id,
                processing_ms=processing_ms,
                whisper_model=self._transcriber.config.model_name,
            )
            return {
                "text": raw_text, "raw_text": raw_text, "corrected": False,
                "snippet_used": False, "language": result.language,
                "duration": result.duration, "processing_ms": processing_ms,
                "id": row_id, "it_wav_path": _it_wav_path,
            }

        result.text, was_corrected, snippet_used, symbol_refs = await self._apply_text_pipeline(
            result, active_mode, user_id, active_app, window_title, selected_text, loop,
        )

        processing_ms = int((time.perf_counter() - t_start) * 1000)
        logger.info("Total stop→result: %dms", processing_ms)

        # Persist
        row_id = await save_transcription(
            text=result.text,
            raw_text=raw_text if was_corrected else None,
            corrected=was_corrected,
            language=result.language,
            duration=result.duration,
            mode=active_mode,
            user_id=user_id,
            tenant_id=tenant_id,
            processing_ms=processing_ms,
            whisper_model=self._transcriber.config.model_name,
        )

        # Pending WAV for user correction training (only when training mode is on)
        _pending_wav_path: str | None = None
        if save_pending_wav and len(audio_data) > 0 and raw_text.strip():
            try:
                import soundfile as _sf
                from pathlib import Path as _Path
                import time as _t
                pending_dir = _Path(__file__).parents[4] / "ml" / "whisper" / "datasets" / "user_corrections" / "pending"
                pending_dir.mkdir(parents=True, exist_ok=True)
                ts = int(_t.time() * 1000)
                pending_wav = pending_dir / f"{ts}.wav"
                _sf.write(str(pending_wav), audio_data, _SAMPLE_RATE)
                _pending_wav_path = str(pending_wav)
                logger.info("Pending WAV saved: %s", pending_wav.name)
            except Exception as e:
                logger.warning("Pending WAV save failed: %s", e)

        logger.info("snippet_used=%s user_id=%s", snippet_used, user_id)
        return {
            "text": result.text,
            "raw_text": raw_text if was_corrected else None,
            "corrected": was_corrected,
            "snippet_used": snippet_used,
            "language": result.language,
            "duration": result.duration,
            "processing_ms": processing_ms,
            "id": row_id,
            "it_wav_path": _it_wav_path,
            "pending_wav_path": _pending_wav_path,
            "symbol_refs": symbol_refs or None,
        }

    async def _apply_text_pipeline(
        self,
        result: "TranscriptionResult",
        active_mode: str,
        user_id: str | None,
        active_app: str | None,
        window_title: str | None,
        selected_text: str | None,
        loop,
    ) -> "tuple[str, bool, bool, list[str]]":
        """Apply the full text post-processing pipeline.

        Returns: (final_text, was_corrected, snippet_used, symbol_refs)

        Pipeline order:
          1. Dictionary substitution (Aho-Corasick / regex fallback)
          2. Snippet expansion
          3. Filler word removal (general/office only)
          4. Engineering symbol injection (engineering only)
          5. LLM correction (if enabled)
        """
        was_corrected = False
        snippet_used = False
        symbol_refs: list[str] = []

        # 1. Dictionary + snippets
        if result.text and user_id:
            entries = await get_dictionary(user_id=user_id, include_smart=True)
            if entries:
                if _HAS_AC:
                    if self._dict_automaton is None or len(entries) != self._dict_entry_count:
                        self._dict_automaton = _build_automaton(entries)
                        self._dict_entry_count = len(entries)
                    result.text = _apply_aho_corasick(result.text, self._dict_automaton)
                    result.text = _apply_aho_corasick(result.text, self._dict_automaton)
                else:
                    result.text = _apply_regex_fallback(result.text, entries)
            snippets = await get_snippets(user_id=user_id)
            if snippets:
                expanded = apply_snippets(result.text, snippets)
                if expanded != result.text:
                    snippet_used = True
                result.text = expanded

        # 2. Filler word removal — deterministic, general/office only
        if result.text and active_mode != "engineering":
            result.text = clean_fillers(result.text)

        # 3. Engineering symbol injection
        if active_mode == "engineering" and result.text and user_id:
            import re as _re
            from .symbol_indexer import inject_symbol_refs as _inject
            injected = await _inject(result.text, user_id)
            if injected != result.text:
                def _fmt_sym(m: "_re.Match") -> str:
                    full_path, name = m.group(1), m.group(2)
                    path_only = full_path.rsplit(":", 1)[0]
                    symbol_refs.append(f"{name} → {full_path}")
                    return f"@{path_only}"
                result.text = _re.sub(r'@([\w/.]+\.\w+:\d+)\s+(\w+)', _fmt_sym, injected)
                _seen_paths = {s.split(" → ", 1)[1].rsplit(":", 1)[0] for s in symbol_refs}
                for _m in _re.finditer(r'@([\w/.]+)', result.text):
                    _path = _m.group(1)
                    if _path not in _seen_paths:
                        _seen_paths.add(_path)
                        _basename = _path.rstrip("/").rsplit("/", 1)[-1] or _path
                        symbol_refs.append(f"{_basename} → {_path}")
                logger.info("Engineering symbols detected: %s", symbol_refs)

        # 4. LLM correction
        if self._corrector.config.enabled and result.text:
            t_llm = time.perf_counter()
            if hasattr(self._corrector, "correct_async"):
                corrected = await self._corrector.correct_async(
                    result.text, result.language, None, active_app,
                    window_title=window_title, selected_text=selected_text,
                )
            else:
                _correct_fn = functools.partial(
                    self._corrector.correct,
                    result.text, result.language, None, active_app,
                    window_title=window_title, selected_text=selected_text,
                )
                corrected = await loop.run_in_executor(_mlx_executor, _correct_fn)
            logger.info("LLM correction: %.3fs", time.perf_counter() - t_llm)
            if corrected != result.text:
                was_corrected = True
                logger.info("Corrected: '%s' → '%s'", result.text[:60], corrected[:60])
            result.text = corrected

        return result.text, was_corrected, snippet_used, symbol_refs

    def force_stop(self) -> bool:
        """Force-stop regardless of state. Returns True if was recording."""
        was_recording = self._audio.is_recording
        if was_recording:
            self._audio.stop()
        else:
            self._audio.force_reset()
        return was_recording

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def update_transcriber(self, new_transcriber: AbstractTranscriber) -> None:
        self._transcriber = new_transcriber

    def update_corrector(self, new_corrector: AbstractCorrector) -> None:
        self._corrector = new_corrector

    @property
    def transcriber(self) -> AbstractTranscriber:
        return self._transcriber

    @property
    def corrector(self) -> AbstractCorrector:
        return self._corrector

    # ------------------------------------------------------------------
    # Model preload (called at startup)
    # ------------------------------------------------------------------

    async def preload_models(self) -> None:
        loop = asyncio.get_running_loop()
        logger.info("Preloading Whisper model...")
        try:
            await loop.run_in_executor(_mlx_executor, self._transcriber._ensure_model_loaded)
            logger.info("Whisper model loaded")
        except Exception as e:
            logger.error("Whisper model load failed: %s", e)

        if self._corrector.config.enabled:
            logger.info("Preloading LLM model...")
            try:
                if hasattr(self._corrector, "correct_async"):
                    await loop.run_in_executor(None, self._corrector._ensure_model_loaded)
                else:
                    await loop.run_in_executor(_mlx_executor, self._corrector._ensure_model_loaded)
                logger.info("LLM model loaded")
            except Exception as e:
                logger.error("LLM model load failed: %s", e)
        else:
            logger.info("LLM correction disabled, skipping preload")
