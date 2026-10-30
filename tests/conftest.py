import numpy as np

KEYWORDS = ["notice", "leave", "hours", "overtime", "salary", "deduct"]


class FakeEmbedder:
    """Keyword-count vectors; text with no keywords gives a zero vector."""

    def embed(self, texts: list[str]) -> np.ndarray:
        rows = [[t.lower().count(k) for k in KEYWORDS] for t in texts]
        return np.array(rows, dtype=np.float32).reshape(len(texts), len(KEYWORDS))
