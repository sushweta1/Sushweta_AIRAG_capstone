"""Week 10 — persistent semantic response cache."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path

import numpy as np


DEFAULT_THRESHOLD = 0.95
DEFAULT_CACHE_PATH = "data/cache/results.db"


def cache_key(question: str, scope: str = "") -> str:
    """Exact question + configuration fingerprint."""
    raw = json.dumps([scope, question], ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cosine_similarity(a, b) -> float:
    """Cosine similarity with dimension and zero-vector checks."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)

    if a.shape != b.shape or a.ndim != 1:
        return -1.0

    if not np.isfinite(a).all() or not np.isfinite(b).all():
        return -1.0

    denominator = np.linalg.norm(a) * np.linalg.norm(b)

    if denominator == 0:
        return -1.0

    return float(np.clip(np.dot(a, b) / denominator, -1, 1))


def identifiers(question: str) -> tuple:
    """Conservative safeguard for numbers and structured IDs."""
    pattern = r"\b[A-Za-z]+[-_]?\d+(?:[.-]\d+)*\b|\b\d+(?:[.-]\d+)*\b"
    return tuple(sorted(re.findall(pattern, question.lower())))


class SemanticCache:
    """SQLite-backed cache scoped to a KB version and RAG configuration."""

    def __init__(
        self,
        path: str = DEFAULT_CACHE_PATH,
        threshold: float = DEFAULT_THRESHOLD,
    ):
        if not 0 < threshold <= 1:
            raise ValueError("threshold must be in (0, 1]")

        self.path = path
        self.threshold = threshold

        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(path, timeout=30)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                key TEXT PRIMARY KEY,
                scope TEXT NOT NULL,
                question TEXT NOT NULL,
                embedding TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_scope
            ON responses(scope)
        """)

        self.conn.commit()

        self.exact_hits = 0
        self.semantic_hits = 0
        self.misses = 0

    def lookup_exact(self, question: str, scope: str):
        """Return the full cached response for an exact match."""

        row = self.conn.execute(
            "SELECT response FROM responses WHERE key = ?",
            (cache_key(question, scope),),
        ).fetchone()

        if row is None:
            return None

        self.exact_hits += 1

        return {
            "response": json.loads(row[0]),
            "similarity": 1.0,
            "match_type": "exact",
        }

    def lookup(self, question: str, embedding: list, scope: str):
        """Find the best semantic match within the same scope."""

        rows = self.conn.execute(
            """
            SELECT question, embedding, response
            FROM responses WHERE scope = ?
            """,
            (scope,),
        ).fetchall()

        best = None
        best_score = -1.0
        query_ids = identifiers(question)

        for stored_question, vector, response in rows:

            # Reject mismatched numbers and identifiers.
            if identifiers(stored_question) != query_ids:
                continue

            score = cosine_similarity(
                embedding,
                json.loads(vector),
            )

            if score >= self.threshold and score > best_score:
                best_score = score
                best = json.loads(response)

        if best is None:
            self.misses += 1
            return None

        self.semantic_hits += 1

        return {
            "response": best,
            "similarity": best_score,
            "match_type": "semantic",
        }

    def put(
        self,
        question: str,
        embedding: list,
        response: dict,
        scope: str,
    ):
        """Store the complete RAG response."""

        self.conn.execute(
            """
            INSERT OR REPLACE INTO responses
            (key, scope, question, embedding, response, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                cache_key(question, scope),
                scope,
                question,
                json.dumps(list(embedding)),
                json.dumps(response),
                time.time(),
            ),
        )

        self.conn.commit()

    def clear(self) -> int:
        """Invalidate all cached responses."""

        cursor = self.conn.execute("DELETE FROM responses")
        self.conn.commit()

        return cursor.rowcount

    def stats(self) -> dict:
        """Return session hit statistics and persistent entry count."""

        entries = self.conn.execute(
            "SELECT COUNT(*) FROM responses"
        ).fetchone()[0]

        hits = self.exact_hits + self.semantic_hits
        total = hits + self.misses

        return {
            "entries": entries,
            "exact_hits": self.exact_hits,
            "semantic_hits": self.semantic_hits,
            "hits": hits,
            "misses": self.misses,
            "total_lookups": total,
            "hit_rate": hits / total if total else 0.0,
        }

    def close(self):
        self.conn.close()
