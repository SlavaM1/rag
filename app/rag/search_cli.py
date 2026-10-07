from __future__ import annotations

import argparse
import json

from .config import Settings
from .search_service import SearchService


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the local RAG knowledge base")
    parser.add_argument("--query", required=True)
    parser.add_argument("--strategy", choices=["fixed", "fixed_no_overlap", "structural"], default="structural")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    results = SearchService(Settings.from_env()).search(args.query, args.strategy, args.top_k)
    print(json.dumps({"query": args.query, "strategy": args.strategy, "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
