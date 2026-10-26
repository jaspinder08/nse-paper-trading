#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

echo "=================================================="
echo "  Starting Independent Trading Engine Worker"
echo "  Mode: Strict Paper Trading"
echo "=================================================="

export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH}"

if [ -f ".venv/bin/python" ]; then
    .venv/bin/python -m trading_engine.worker
else
    python3 -m trading_engine.worker
fi
