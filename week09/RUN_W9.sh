#!/usr/bin/env bash
# W9 reference package — convenience runner.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# BLAS thread limits at shell level
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export TOKENIZERS_PARALLELISM=false

# PYTHONPATH so subprocesses can import src.*
export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"

echo "=== W9 Reference Runner ==="
echo ""

PYTHON=${PYTHON:-python3}
$PYTHON --version

if [ "${1:-}" = "--install" ]; then
    echo "Installing dependencies..."
    $PYTHON -m pip install -r requirements.txt
    echo ""
    echo "Note: sentence-transformers brings PyTorch (~500 MB)."
    echo "First rerank() call will also download the cross-encoder model (~80 MB)."
    echo ""
fi

# Load .env before checking credentials.
if [ "${W9_ENV_LOADED:-0}" != "1" ]; then
    exec "$PYTHON" - "$@" <<'ENV_PY'
import os
import sys
from dotenv import load_dotenv

load_dotenv(".env", override=False)
os.environ["W9_ENV_LOADED"] = "1"

args = [arg for arg in sys.argv[1:] if arg != "--install"]
os.execvpe("bash", ["bash", "RUN_W9.sh", *args], os.environ)
ENV_PY
fi

if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "ERROR: OPENAI_API_KEY environment variable is not set."
    echo "Hint: configure OPENAI_API_KEY in .env or the environment."
    exit 1
fi

if [ -n "${QDRANT_URL:-}" ]; then
    if [ -n "${QDRANT_API_KEY:-}" ]; then
        echo "Qdrant mode: Cloud — $QDRANT_URL"
    else
        echo "Qdrant mode: local (Docker) — $QDRANT_URL"
    fi
else
    echo "Qdrant mode: NOT CONFIGURED (live tests will SKIP)"
fi
echo ""

echo "Running W9 verifier..."
echo ""
$PYTHON verify_w9.py
