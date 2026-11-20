"""Bootstrap module — environment setup for W7.

Two things this module handles:

1. Thread limits — Vocareum's RLIMIT_NPROC is tight; BLAS multi-
   threading triggers "Resource temporarily unavailable" errors when
   numpy/sentence-transformers tries to spawn worker threads.

2. (Not needed for W7 — kept here as a placeholder for W8+ where we
   may add sentence-transformers and PII libraries that have their
   own constraints.)

Must run BEFORE any numpy import. Import this module first in every
entry point — even before scripts/build_index.py and verify_w7.py.

Idempotent. Safe to import multiple times.
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv


def _setup_thread_limits() -> None:
    """Constrain BLAS thread spawning."""
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
    os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def setup() -> None:
    """Run all bootstrap fixes. Call before numpy / qdrant_client imports."""
    _setup_thread_limits()
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env", override=False)


setup()
