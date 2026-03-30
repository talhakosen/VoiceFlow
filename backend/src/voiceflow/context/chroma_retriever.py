"""ChromaDB-based RAG retriever.

Uses sentence-transformers/all-MiniLM-L6-v2 for embeddings (CPU, ~22MB, ~30ms/query).
PersistentClient stores index at ~/.voiceflow/chroma/
"""

import logging
import os
import threading
from pathlib import Path

from ..core.interfaces import AbstractRetriever

logger = logging.getLogger(__name__)

_CHROMA_PATH = Path(os.getenv("CHROMA_PATH", str(Path.home() / ".voiceflow" / "chroma")))
_DEFAULT_TENANT = "default"


class ChromaRetriever(AbstractRetriever):
    """Retrieves relevant context chunks from ChromaDB."""

    def __init__(self, tenant_id: str = _DEFAULT_TENANT) -> None:
        self._tenant_id = tenant_id
        self._collection_name = f"kb_{tenant_id}"
        self._client = None
        self._collection = None
        self._lock = threading.Lock()

    def _ensure_collection(self):
        """Lazy-initialize ChromaDB client and collection. Thread-safe."""
        if self._collection is not None:
            return
        with self._lock:
            if self._collection is not None:  # double-checked locking
                return

            import chromadb
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

            _CHROMA_PATH.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(_CHROMA_PATH))

            ef = SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2",
                device="cpu",
            )
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "ChromaDB collection '%s' ready (%d chunks)",
                self._collection_name,
                self._collection.count(),
            )

    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        """Return top-k relevant text chunks. Returns [] if collection is empty."""
        if not query or not query.strip():
            return []

        self._ensure_collection()

        n = self._collection.count()
        if n == 0:
            return []

        results = self._collection.query(
            query_texts=[query],
            n_results=min(top_k, n),
            include=["documents"],
        )
        docs = results.get("documents", [[]])[0]
        logger.debug("Retrieved %d context chunks for query: '%s'", len(docs), query[:60])
        return docs

    def is_empty(self) -> bool:
        self._ensure_collection()
        return self._collection.count() == 0

    def count(self) -> int:
        self._ensure_collection()
        return self._collection.count()

    def clear(self) -> None:
        """Delete and recreate the collection (wipes all indexed content)."""
        if self._client is None:
            self._ensure_collection()
        try:
            self._client.delete_collection(self._collection_name)
            logger.info("ChromaDB collection '%s' cleared", self._collection_name)
        except Exception as e:
            logger.warning("Clear collection failed: %s", e)
        self._collection = None
        self._ensure_collection()

    def add_chunks(self, chunks: list[str], ids: list[str]) -> None:
        """Add pre-chunked text with given IDs. Skips existing IDs."""
        self._ensure_collection()
        if not chunks:
            return
        self._collection.upsert(documents=chunks, ids=ids)
        logger.debug("Upserted %d chunks into '%s'", len(chunks), self._collection_name)
