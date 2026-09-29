import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.evaluation import compare, write_report


if __name__ == "__main__":
    report = write_report(compare())
    print(f"Comparison report written to {report}")
