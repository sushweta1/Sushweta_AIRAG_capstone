"""W4 REFERENCE — src/api/main.py

W3 contract preserved:
  POST /ask           — streams text/plain
  POST /ask_batched   — returns Answer JSON
  GET  /health        — {"status": "ok"}

W4 changes to the BODY (not the contract):
  • ask_llm now uses tool-calling → richer Answer (confidence, sources,
    schema_version) and real cost_usd.
  • /ask now streams REAL OpenAI chunks (not asyncio.sleep simulation).
  • Each /ask_batched call is persisted to SQLite with model + cost_usd.

Old clients see additive fields in the JSON response; they keep working.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from src.pipeline.models import Answer, Question
from src.pipeline.pipeline import ask_llm, stream_answer
from src.pipeline.settings import Settings
from src.pipeline.store import connect, save_answer

from functools import lru_cache

from fastapi.concurrency import run_in_threadpool

from src.pipeline.cost import compute_cost_usd
from src.rag.qdrant_rag import ask_rag, CHAT_MODEL
from src.rag.qdrant_store import load_store

logger = logging.getLogger(__name__)

app = FastAPI(title="Capstone API — W4")

# Single Settings instance — read once at startup.
_settings = Settings()
_db_path = Path(_settings.results_db)

@lru_cache(maxsize=1)
def get_rag_store():
    """Create the Qdrant connection once and reuse it."""
    return load_store()


@app.get("/health")
async def health() -> dict:
    """Unchanged from W3."""
    return {"status": "ok"}


@app.post("/ask_batched", response_model=Answer)
async def ask_batched(q: Question) -> Answer:
    """Return a RAG-grounded Answer and persist it to SQLite."""

    # Retrieve relevant documents and generate an answer.
    rag_result = await run_in_threadpool(
        ask_rag,
        q.question,
        get_rag_store(),
        _settings,
    )

    # Calculate the chat-completion cost using existing W5 logic.
    chat_cost = compute_cost_usd(
        CHAT_MODEL,
        rag_result["tokens_in"],
        rag_result["tokens_out"],
    )

    # Preserve the existing Answer schema.
    answer = Answer(
        content=rag_result["answer"],
        sources=rag_result["sources"],
        cost_usd=chat_cost,
        retries=0,
        confidence=1.0,
        schema_version="v1",
    )

    # Preserve existing SQLite persistence.
    with connect(_db_path) as conn:
        save_answer(
            conn,
            question=q.question,
            content=answer.content,
            retries=answer.retries,
            cost_usd=answer.cost_usd,
            model=CHAT_MODEL,
            confidence=answer.confidence,
            sources=answer.sources,
            schema_version=answer.schema_version,
        )

    return answer



@app.post("/ask")
async def ask(q: Question) -> StreamingResponse:
    """Real streaming text/plain. Same URL + same input as W3."""
    async def _gen():
        async for chunk in stream_answer(q.question, _settings):
            yield chunk
    return StreamingResponse(_gen(), media_type="text/plain")
