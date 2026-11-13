"""Embeddings — OpenAI wrapper with JSON cache.

W6 had `embed(texts)` hardcoded to text-embedding-3-small.
W7 extends this with a `model` parameter so learners can compare
text-embedding-3-small vs text-embedding-3-large.

The JSON cache from W6 is preserved. The cache key includes the
model name, so swapping models doesn't get false cache hits.

Both models are OpenAI hosted:
- text-embedding-3-small: 1536 dims, $0.02 / 1M tokens
- text-embedding-3-large: 3072 dims, $0.13 / 1M tokens

Local embeddings (sentence-transformers BGE/Nomic) are introduced
as an OPTIONAL stretch path via the W7 activity.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from openai import OpenAI


# Lazy-load the OpenAI client so importing this module doesn't require
# an API key — useful for smoke tests, offline syntax checks, etc.
_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


# Per-1M-token rates (input only — embeddings have no output)
EMBEDDING_RATES = {
    "text-embedding-3-small": 0.02 / 1_000_000,
    "text-embedding-3-large": 0.13 / 1_000_000,
}


# Vector dimensions per model (useful for sanity-checks and Qdrant
# collection creation)
EMBEDDING_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}


def _cache_key(text: str, model: str) -> str:
    """SHA256 of (model + text). Including the model name means swapping
    models triggers a fresh embed rather than a false cache hit."""
    h = hashlib.sha256()
    h.update(model.encode("utf-8"))
    h.update(b"\x00")
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def load_cache(path: str = "data/embeddings.json") -> dict[str, list[float]]:
    """Load the JSON cache from disk. Returns {} if not present."""
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def save_cache(cache: dict[str, list[float]], path: str = "data/embeddings.json") -> None:
    """Write the cache to disk."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cache))


def embed(texts: list[str], model: str = "text-embedding-3-small",
          cache_path: str | None = "data/embeddings.json") -> list[list[float]]:
    """Embed a list of texts via OpenAI. Cached by sha256(model + text).

    Args:
        texts: list of strings to embed.
        model: OpenAI embedding model name.
        cache_path: where to read/write the JSON cache. Pass None to disable caching.

    Returns:
        list of vectors, in the same order as `texts`.
    """
    if not texts:
        return []

    if model not in EMBEDDING_RATES:
        raise ValueError(
            f"Unknown embedding model: {model}. "
            f"Supported: {list(EMBEDDING_RATES.keys())}"
        )

    cache = load_cache(cache_path) if cache_path else {}

    # Figure out which texts are cache-misses
    keys = [_cache_key(t, model) for t in texts]
    missing_indices = [i for i, k in enumerate(keys) if k not in cache]

    if missing_indices:
        missing_texts = [texts[i] for i in missing_indices]
        # OpenAI batch embed (one API call)
        response = _get_client().embeddings.create(model=model, input=missing_texts)
        for i, item in zip(missing_indices, response.data):
            cache[keys[i]] = item.embedding
        if cache_path:
            save_cache(cache, cache_path)

    return [cache[k] for k in keys]


def estimate_embedding_cost(num_tokens: int, model: str) -> float:
    """Estimate cost in USD for embedding `num_tokens` tokens with `model`."""
    rate = EMBEDDING_RATES.get(model)
    if rate is None:
        raise ValueError(f"Unknown model: {model}")
    return num_tokens * rate
