#!/usr/bin/env bash
# W8 reference package — convenience runner.
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

echo "=== W8 Reference Runner ==="
echo ""

PYTHON=${PYTHON:-python3}
$PYTHON --version

if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "ERROR: OPENAI_API_KEY environment variable is not set."
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

if [ "${1:-}" = "--install" ]; then
    echo "Installing dependencies..."
    $PYTHON -m pip install -r requirements.txt
    echo ""
fi

echo "Running W8 verifier..."
echo ""
$PYTHON verify_w8.py
