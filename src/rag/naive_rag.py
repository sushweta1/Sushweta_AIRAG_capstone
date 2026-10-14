"""Naive RAG for the FastAPI Knowledge Assistant — W6."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from openai import OpenAI

from src.pipeline.settings import Settings

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"

_client = None

def _openai() -> OpenAI:
    """Create the OpenAI client only when first needed."""
    global _client
    if _client is None:
        _client = OpenAI()
    return _client

# ─── Chunking ─────────────────────────────────────────

def chunk_text(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping character-based chunks."""
    if len(text) <= size:
        return [text]

    chunks = []
    i = 0

    while i < len(text):
        end = min(i + size, len(text))
        chunks.append(text[i:end])

        if end == len(text):
            break

        i = end - overlap

    return chunks

# ─── Corpus loading ───────────────────────────────────

def load_corpus(corpus_dir: Path) -> list[dict]:
    """Load Markdown and text files and assign chunk IDs."""
    all_chunks = []

    for path in sorted(corpus_dir.glob("*")):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue

        text = path.read_text(encoding="utf-8")

        for idx, chunk in enumerate(chunk_text(text)):
            all_chunks.append({
                "chunk_id": f"{path.stem}#{idx}",
                "source_id": path.stem,
                "text": chunk,
            })

    return all_chunks

# ─── Embedding generation ─────────────────────────────

def embed_batch(texts: list[str]) -> list[list[float]]:
    """Convert a batch of text passages into embedding vectors."""
    resp = _openai().embeddings.create(
        model=EMBED_MODEL,
        input=texts
    )
    return [item.embedding for item in resp.data]

def build_index(chunks: list[dict]) -> list[dict]:
    """Generate embeddings and attach them to the chunks."""
    texts = [c["text"] for c in chunks]

    # Process at most 100 chunks per API request
    for i in range(0, len(texts), 100):
        batch = texts[i:i + 100]
        vectors = embed_batch(batch)

        for chunk, vec in zip(chunks[i:i + 100], vectors):
            chunk["vector"] = vec

    return chunks

# ─── Index persistence ────────────────────────────────

def save_index(index: list[dict], path: Path) -> None:
    """Save indexed chunks and their vectors to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(index, ensure_ascii=False),
        encoding="utf-8"
    )

def load_index(path: Path) -> list[dict]:
    """Load previously saved chunks and embeddings."""
    return json.loads(path.read_text(encoding="utf-8"))

# ─── Similarity calculation ───────────────────────────

def cosine(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)

    denominator = np.linalg.norm(a) * np.linalg.norm(b)

    if denominator == 0:
        return 0.0

    return float(np.dot(a, b) / denominator)

# ─── Retrieval ────────────────────────────────────────

def retrieve(
    query: str,
    index: list[dict],
    k: int = 5
) -> list[dict]:
    """Return the K most similar document chunks."""

    # Convert the user's question into an embedding
    query_vector = embed_batch([query])[0]

    # Compare the question with every indexed chunk
    scored = []

    for chunk in index:
        score = cosine(query_vector, chunk["vector"])

        scored.append({
            **chunk,
            "score": score
        })

    # Highest similarity first
    scored.sort(key=lambda x: x["score"], reverse=True)

    return scored[:k]

# ─── Grounded answer generation ───────────────────────

SYSTEM = """
You are a FastAPI documentation assistant.

Answer the user's question using only the supplied context.

Rules:
1. Do not invent information that is not in the context.
2. If the context does not contain the answer, say that
   you cannot determine it from the provided documentation.
3. Cite the relevant source chunk IDs in your answer,
   using the format [source_id#chunk_number].
4. Keep answers clear and concise.
"""
def ask_rag(
    question: str,
    index: list[dict],
    settings: Settings,
    k: int = 5
) -> dict[str, Any]:
    """Retrieve evidence and generate a grounded answer."""

    # Step 1: Retrieve relevant document chunks
    hits = retrieve(question, index, k=k)

    # Step 2: Prepare the context for the LLM
    context = "\n\n".join(
        f"[{hit['chunk_id']}]\n{hit['text']}"
        for hit in hits
    )

    # Step 3: Ask the LLM to answer using that context
    response = _openai().chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Context:\n{context}\n\n"
                    f"Question: {question}"
                ),
            },
        ],
    )

    # Step 4: Extract the generated answer
    answer = response.choices[0].message.content or ""

    # Step 5: Return answer, sources and token usage
    return {
        "answer": answer,
        "sources": [hit["chunk_id"] for hit in hits],
        "tokens_in": response.usage.prompt_tokens if response.usage else 0,
        "tokens_out": response.usage.completion_tokens if response.usage else 0,
    }