"""Qdrant-backed RAG pipeline — W8 reference implementation.

Extends W7's ask_rag with:
  1. Optional metadata `filter` parameter — backward compatible.
  2. Richer citations — sources now include section_path + page.

Same shape otherwise. Existing W7 callers work unchanged.

Usage (W7-equivalent):
    from src.rag.qdrant_store import load_store
    from src.rag.qdrant_rag import ask_rag

    store = load_store(embedding_model="text-embedding-3-small", dim=1536)
    result = ask_rag("What is the leave policy?", store)
    print(result["answer"])

Usage (W8 — with metadata filter):
    from src.rag.qdrant_store import eq

    result = ask_rag(
        "What's our IT incident process?",
        store,
        filter=eq("doc_type", "it"),
    )
"""
from __future__ import annotations

# Bootstrap before any heavy import
from src import _bootstrap  # noqa: F401

import time
from typing import Any, Optional

from openai import OpenAI

from src.rag.embeddings import embed
from src.rag.qdrant_store import QdrantStore, retrieve


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


def ask_rag(question: str,
            store: QdrantStore,
            k: int = 3,
            filter: Optional[Any] = None,
            chat_model: str = "gpt-4o-mini",
            temperature: float = 0.0) -> dict:
    """Answer a question with top-k retrieval, optionally filtered.

    Args:
        question: The user's question.
        store: A QdrantStore handle.
        k: Number of chunks to retrieve.
        filter: Optional Qdrant filter (use src.rag.qdrant_store.eq /
            combine_and / combine_or to build).
        chat_model: OpenAI chat model.
        temperature: Sampling temperature.

    Returns:
        Dict with answer, sources, citations, cost, latency, etc.
    """
    start = time.time()

    # Step 1 — embed the question
    query_embedding = embed([question], model=store.embedding_model)[0]

    # Step 2 — retrieve top-k (with optional filter)
    retrieved = retrieve(store, query_embedding, k=k, filter=filter)

    # Step 3 — build the prompt with rich citations
    context_parts = []
    for r in retrieved:
        citation = r["source"]
        if r["section_path"]:
            citation += f" — {r['section_path']}"
        if r["page"]:
            citation += f" (p. {r['page']})"
        context_parts.append(f"=== {citation} ===\n{r['text']}")
    context = "\n\n".join(context_parts)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Question: {question}\n\nDocuments:\n{context}"},
    ]

    # Step 4 — generate
    response = _get_client().chat.completions.create(
        model=chat_model,
        messages=messages,
        temperature=temperature,
    )

    latency_ms = int((time.time() - start) * 1000)
    usage = response.usage
    rates = CHAT_RATES.get(chat_model, {"in": 0, "out": 0})
    chat_cost = usage.prompt_tokens * rates["in"] + usage.completion_tokens * rates["out"]

    return {
        "answer": response.choices[0].message.content,
        "sources": [r["source"] for r in retrieved],
        "citations": [
            {
                "source": r["source"],
                "doc_title": r["doc_title"],
                "section_path": r["section_path"],
                "page": r["page"],
                "score": r["score"],
            }
            for r in retrieved
        ],
        "retrieved_chunks": [r["text"][:200] for r in retrieved],
        "cost_usd": chat_cost,
        "latency_ms": latency_ms,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "chat_model": chat_model,
        "embedding_model": store.embedding_model,
        "filter_used": filter is not None,
    }
