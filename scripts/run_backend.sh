#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

echo "=================================================="
echo "  Starting FastAPI Backend Server"
echo "  URL: http://127.0.0.1:8000"
echo "  Swagger Docs: http://127.0.0.1:8000/docs"
echo "=================================================="

export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH}"

if [ -f ".venv/bin/uvicorn" ]; then
    .venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
else
    uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
fi
