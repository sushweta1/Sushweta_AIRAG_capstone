"""Qdrant-backed RAG pipeline for the FastAPI Knowledge Assistant."""

from __future__ import annotations

from openai import OpenAI

from src.rag.qdrant_store import QdrantStore, load_store

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"

SYSTEM = """You are a helpful FastAPI documentation assistant.

Answer questions using only the retrieved documentation context.

If the context does not contain enough information, say that you
cannot determine the answer from the provided documentation.

Use clear, concise explanations.

Cite supporting document chunks using their exact chunk IDs
in square brackets, for example [path_parameters#0].

Do not invent citations or unsupported information.
"""


def embed_query(question: str) -> list[float]:
    """Convert a question into an embedding vector."""

    client = OpenAI()

    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=question,
    )

    return response.data[0].embedding


def retrieve(
    question: str,
    store: QdrantStore,
    k: int = 5,
) -> list[dict]:
    """Retrieve the top-k relevant chunks from Qdrant."""

    vector = embed_query(question)

    response = store.client.query_points(
        collection_name=store.collection,
        query=vector,
        limit=k,
        with_payload=True,
    )

    chunks = []

    for point in response.points:
        payload = point.payload or {}

        chunks.append({
            "chunk_id": payload.get("chunk_id", ""),
            "source_id": payload.get("source_id", ""),
            "text": payload.get("text", ""),
            "score": point.score,
        })

    return chunks


def ask_rag(
    question: str,
    store: QdrantStore | None = None,
    settings=None,
    k: int = 5,
) -> dict:
    """Answer a question using Qdrant retrieval and GPT-4o-mini."""

    if store is None:
        store = load_store()

    chunks = retrieve(question, store, k=k)

    context = "\n\n".join(
        f"[{chunk['chunk_id']}]\n{chunk['text']}"
        for chunk in chunks
    )

    client = OpenAI()

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Documentation context:\n{context}\n\n"
                    f"Question: {question}"
                ),
            },
        ],
    )

    answer = response.choices[0].message.content or ""
    usage = response.usage

    return {
        "answer": answer,
        "sources": [chunk["chunk_id"] for chunk in chunks],
        "chunk_ids": [chunk["chunk_id"] for chunk in chunks],
        "tokens_in": usage.prompt_tokens if usage else 0,
        "tokens_out": usage.completion_tokens if usage else 0,
    }
