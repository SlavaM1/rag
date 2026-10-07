#!/bin/sh
set -eu

if [ ! -f data/rag/fixed/index.faiss ] || [ ! -f data/rag/fixed/metadata.json ] || \
   [ ! -f data/rag/structural/index.faiss ] || [ ! -f data/rag/structural/metadata.json ]; then
  python -m app.rag.indexer
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
