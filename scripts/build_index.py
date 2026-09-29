import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.indexer import _print_stats, build_indexes


if __name__ == "__main__":
    _print_stats(build_indexes())
