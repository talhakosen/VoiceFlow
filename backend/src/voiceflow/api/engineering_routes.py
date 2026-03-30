"""Engineering Package API routes — K3.

POST /api/engineering/extract-symbols  → extract symbols, add to user dictionary
POST /api/engineering/index-repo       → index git repo into ChromaDB (background)
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from .auth import verify_api_key
from ..db import add_dictionary_entry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/engineering", dependencies=[Depends(verify_api_key)])


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

class ExtractSymbolsRequest(BaseModel):
    repo_path: str


class ExtractSymbolsResponse(BaseModel):
    added: int
    symbols: list[str]


class IndexRepoRequest(BaseModel):
    repo_path: str


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("/extract-symbols", response_model=ExtractSymbolsResponse)
async def extract_symbols_endpoint(
    body: ExtractSymbolsRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """Extract code symbols from repo and add them to the team dictionary."""
    from ..services.engineering import extract_symbols

    loop = asyncio.get_running_loop()
    symbols = await loop.run_in_executor(None, extract_symbols, body.repo_path)

    if not symbols:
        return ExtractSymbolsResponse(added=0, symbols=[])

    user_id = x_user_id or ""
    added = 0
    for symbol in symbols:
        try:
            await add_dictionary_entry(
                trigger=symbol,
                replacement=symbol,
                user_id=user_id,
                scope="team",
            )
            added += 1
        except Exception as e:
            # Ignore duplicate key / DB errors per symbol
            logger.debug("extract_symbols: skip symbol %s: %s", symbol, e)

    logger.info("extract_symbols: added %d/%d symbols to dictionary", added, len(symbols))
    return ExtractSymbolsResponse(added=added, symbols=symbols)


@router.post("/index-repo")
async def index_repo_endpoint(
    body: IndexRepoRequest,
    request: Request,
):
    """Index a git repo into ChromaDB (background task)."""
    from ..services.engineering import ingest_git_repo
    from ..context.chroma_retriever import ChromaRetriever

    loop = asyncio.get_running_loop()

    async def _run():
        svc = request.app.state.recording_service
        retriever = svc.retriever
        if retriever is None:
            retriever = ChromaRetriever()
            svc.update_retriever(retriever)

        result = await loop.run_in_executor(
            None, ingest_git_repo, body.repo_path, "default", retriever
        )
        logger.info(
            "index_repo done: %d files, %d chunks, %d errors",
            result.files_processed, result.chunks_added, len(result.errors),
        )

    task = asyncio.create_task(_run())
    request.app.state.engineering_ingest_task = task

    return {"status": "started", "repo_path": body.repo_path, "message": "Git repo indexing in background"}
