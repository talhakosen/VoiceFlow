"""File ingestion pipeline for the VoiceFlow context engine.

Walks a folder, reads supported text files, chunks them, and upserts into ChromaDB.
Designed to be run by VoiceFlow admin during on-site setup — not by end users.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Supported file extensions (minimal per Phase 2 scope)
_SUPPORTED_EXTENSIONS = {
    ".txt", ".md", ".py", ".swift",
    ".ts", ".js", ".go", ".java",
    ".yaml", ".yml", ".json", ".toml",
    ".rs", ".cpp", ".c", ".h",
}

_MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB per file
_CHUNK_SIZE = 1000         # characters
_CHUNK_OVERLAP = 100       # characters


@dataclass
class IngestResult:
    files_processed: int = 0
    chunks_added: int = 0
    files_skipped: int = 0
    errors: list[str] = field(default_factory=list)


def _chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c for c in chunks if c.strip()]


def _file_chunk_id(file_path: Path, chunk_index: int) -> str:
    """Stable, unique ID for a chunk: hash(absolute_path):chunk_index."""
    path_hash = hashlib.md5(str(file_path.resolve()).encode()).hexdigest()[:12]
    return f"{path_hash}:{chunk_index}"


def ingest_folder(
    folder_path: str,
    tenant_id: str = "default",
    retriever=None,
) -> IngestResult:
    """Walk folder_path, read supported files, chunk, and upsert into ChromaDB.

    Args:
        folder_path: Directory to index recursively.
        tenant_id: Tenant identifier (used only when retriever is None).
        retriever: AbstractRetriever instance to write to. Created if None.

    This is a synchronous, potentially long-running function.
    Call via run_in_executor from async routes.
    """
    from .chroma_retriever import ChromaRetriever

    result = IngestResult()
    if retriever is None:
        retriever = ChromaRetriever(tenant_id=tenant_id)
    root = Path(folder_path).expanduser().resolve()

    if not root.exists():
        result.errors.append(f"Path does not exist: {folder_path}")
        return result

    if not root.is_dir():
        result.errors.append(f"Not a directory: {folder_path}")
        return result

    logger.info("Ingesting folder: %s (tenant=%s)", root, tenant_id)

    for file_path in root.rglob("*"):
        # Skip hidden files/dirs and __pycache__
        if any(part.startswith(".") or part == "__pycache__" for part in file_path.parts):
            continue
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
            continue
        if file_path.stat().st_size > _MAX_FILE_SIZE_BYTES:
            logger.debug("Skipping large file: %s", file_path.name)
            result.files_skipped += 1
            continue

        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
            if not text:
                result.files_skipped += 1
                continue

            chunks = _chunk_text(text)
            if not chunks:
                result.files_skipped += 1
                continue

            ids = [_file_chunk_id(file_path, i) for i in range(len(chunks))]
            retriever.add_chunks(chunks, ids)

            result.files_processed += 1
            result.chunks_added += len(chunks)
            logger.debug("Indexed %s → %d chunks", file_path.name, len(chunks))

        except Exception as e:
            logger.warning("Failed to index %s: %s", file_path, e)
            result.errors.append(f"{file_path.name}: {e}")

    logger.info(
        "Ingestion complete: %d files, %d chunks, %d skipped, %d errors",
        result.files_processed, result.chunks_added, result.files_skipped, len(result.errors),
    )
    return result
