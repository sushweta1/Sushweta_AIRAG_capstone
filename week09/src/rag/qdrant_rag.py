"""Qdrant-backed RAG pipeline — W9 reference implementation.

Extends W8's ask_rag with an optional `retrieval_method` parameter.
Backward compatible: default is 'dense', which matches W8 exactly.

Usage (W8-equivalent):
    result = ask_rag("What is the leave policy?", store)

Usage (W9 — hybrid):
    result = ask_rag("...", store, retrieval_method='hybrid',
                     bm25_index=bm25, chunks=chunks)

Usage (W9 — hybrid + rerank):
    result = ask_rag("...", store, retrieval_method='hybrid_rerank',
                     bm25_index=bm25, chunks=chunks)
"""
from __future__ import annotations

# Bootstrap before any heavy import
from src import _bootstrap  # noqa: F401

import time
from typing import Any, Optional

from openai import OpenAI

from src.rag.embeddings import embed
from src.rag.qdrant_store import QdrantStore, retrieve as qdrant_retrieve


# Lazy-load the OpenAI client
_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


SYSTEM_PROMPT = (
    "You are an internal knowledge assistant. Answer the user's question "
    "using only the policy documents provided below. If the documents don't "
    "contain the answer, say so honestly. Cite the source document name(s) "
    "and section(s) you used."
)


CHAT_RATES = {
    "gpt-4o-mini": {"in": 0.15 / 1_000_000, "out": 0.60 / 1_000_000},
    "gpt-4o":      {"in": 2.50 / 1_000_000, "out": 10.00 / 1_000_000},
}


VALID_METHODS = ("dense", "hybrid", "hybrid_rerank")


def ask_rag(
    question: str,
    store: QdrantStore,
    k: int = 3,
    filter: Optional[Any] = None,
    retrieval_method: str = "dense",
    bm25_index: Any = None,
    chunks: Optional[list] = None,
    chat_model: str = "gpt-4o-mini",
    temperature: float = 0.0,
) -> dict:
    """Answer a question with top-k retrieval.

    Args:
        question: The user's question.
        store: A QdrantStore handle.
        k: Number of chunks to use in the prompt.
        filter: Optional Qdrant filter (use src.rag.qdrant_store.eq /
            combine_and / combine_or to build).
        retrieval_method: 'dense' (W8 behaviour, default), 'hybrid', or
            'hybrid_rerank'. The non-dense methods require bm25_index +
            chunks to be passed.
        bm25_index: Required if retrieval_method != 'dense'. Built via
            src.rag.retrieval.build_bm25_index().
        chunks: Required if retrieval_method != 'dense'. The same chunks
            list used to build bm25_index.
        chat_model: OpenAI chat model.
        temperature: Sampling temperature.

    Returns:
        Dict with answer, sources, citations, cost, latency, etc.
    """
    if retrieval_method not in VALID_METHODS:
        raise ValueError(
            f"retrieval_method must be one of {VALID_METHODS}, "
            f"got {retrieval_method!r}"
        )
    if retrieval_method != "dense" and (bm25_index is None or chunks is None):
        raise ValueError(
            f"retrieval_method={retrieval_method!r} requires "
            f"bm25_index and chunks; pass both."
        )

    start = time.time()
    retrieve_ms = 0
    embed_ms = 0

    # ── Retrieval — dispatch on method ──────────────────────────────────
    if retrieval_method == "dense":
        t0 = time.time()
        query_embedding = embed([question], model=store.embedding_model)[0]
        embed_ms = int((time.time() - t0) * 1000)
        t0 = time.time()
        retrieved = qdrant_retrieve(store, query_embedding, k=k, filter=filter)
        retrieve_ms = int((time.time() - t0) * 1000)

    elif retrieval_method == "hybrid":
        from src.rag.retrieval import hybrid_retrieve
        t0 = time.time()
        retrieved = hybrid_retrieve(
            store=store, bm25_index=bm25_index, chunks=chunks,
            query=question, k_each=10, k_final=k, filter=filter,
        )
        retrieve_ms = int((time.time() - t0) * 1000)

    else:  # hybrid_rerank
        from src.rag.retrieval import hybrid_rerank_retrieve
        t0 = time.time()
        retrieved = hybrid_rerank_retrieve(
            store=store, bm25_index=bm25_index, chunks=chunks,
            query=question, k_candidates=20, top_k=k, filter=filter,
        )
        retrieve_ms = int((time.time() - t0) * 1000)

    # ── Build the prompt with rich citations ────────────────────────────
    context_parts = []
    for r in retrieved:
        source = r.get("source") or "unknown"
        citation = source
        section_path = r.get("section_path") or ""
        page = r.get("page")
        if section_path:
            citation += f" — {section_path}"
        if page is not None:
            citation += f" (p. {page})"
        context_parts.append(f"=== {citation} ===\n{r.get('text', '')}")
    context = "\n\n".join(context_parts)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Question: {question}\n\nDocuments:\n{context}"},
    ]

    # ── Generate ────────────────────────────────────────────────────────
    t0 = time.time()
    response = _get_client().chat.completions.create(
        model=chat_model,
        messages=messages,
        temperature=temperature,
    )
    generate_ms = int((time.time() - t0) * 1000)

    total_ms = int((time.time() - start) * 1000)
    usage = response.usage
    rates = CHAT_RATES.get(chat_model, {"in": 0, "out": 0})
    chat_cost = usage.prompt_tokens * rates["in"] + usage.completion_tokens * rates["out"]

    return {
        "answer": response.choices[0].message.content,
        "sources": [r.get("source") or "unknown" for r in retrieved],
        "citations": [
            {
                "source": r.get("source") or "unknown",
                "doc_title": r.get("doc_title", ""),
                "section_path": r.get("section_path", ""),
                "page": r.get("page"),
                "score": r.get("score", 0.0),
                "dense_rank": r.get("dense_rank"),
                "bm25_rank": r.get("bm25_rank"),
                "pre_rerank_rank": r.get("pre_rerank_rank"),
            }
            for r in retrieved
        ],
        "retrieved_chunks": [r.get("text", "")[:200] for r in retrieved],
        "cost_usd": chat_cost,
        "latency_ms": total_ms,
        "embed_ms": embed_ms,
        "retrieve_ms": retrieve_ms,
        "generate_ms": generate_ms,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "chat_model": chat_model,
        "embedding_model": store.embedding_model,
        "retrieval_method": retrieval_method,
        "filter_used": filter is not None,
    }
