"""Build the knowledge base: python scripts/build_kb.py (from repo root)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.knowledge_base import build_kb  # noqa: E402
from src.rag_pipeline import OpenAIEmbedder  # noqa: E402

if __name__ == "__main__":
    n = build_kb("data/knowledge_base/sources.json", "data/knowledge_base", OpenAIEmbedder())
    print(f"Built knowledge base with {n} passages")
