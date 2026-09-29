#!/bin/sh
set -eu

if [ ! -f data/rag/fixed/index.faiss ] || [ ! -f data/rag/structural/index.faiss ]; then
  python -m app.rag.indexer
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
