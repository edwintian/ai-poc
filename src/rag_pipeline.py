import json
from pathlib import Path

import faiss
import numpy as np
import openai

from src.config import get_secret
from src.schemas import Hit, Passage


class RetrievalError(Exception):
    pass


class OpenAIEmbedder:
    BATCH = 100

    def __init__(self, client=None, model: str = "text-embedding-3-small"):
        self._client = client
        self.model = model

    def _get_client(self):
        if self._client is None:
            self._client = openai.OpenAI(api_key=get_secret("OPENAI_API_KEY"))
        return self._client

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        rows: list[list[float]] = []
        try:
            client = self._get_client()
            for i in range(0, len(texts), self.BATCH):
                resp = client.embeddings.create(model=self.model, input=texts[i:i + self.BATCH])
                rows.extend(d.embedding for d in resp.data)
        except openai.OpenAIError as e:
            raise RetrievalError(f"Embedding request failed: {e}") from e
        return np.asarray(rows, dtype=np.float32)


def _normalise(m: np.ndarray) -> np.ndarray:
    m = np.ascontiguousarray(m, dtype=np.float32)
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return m / norms


class VectorStore:
    def __init__(self, passages: list[Passage], vectors: np.ndarray):
        vectors = np.asarray(vectors, dtype=np.float32)
        if len(passages) != len(vectors):
            raise ValueError(f"{len(passages)} passages but {len(vectors)} vectors")
        self.passages = passages
        self.vectors = _normalise(vectors) if len(vectors) else vectors.reshape(0, vectors.shape[-1] if vectors.ndim == 2 else 0)
        self.index = None
        if len(passages):
            self.index = faiss.IndexFlatIP(self.vectors.shape[1])
            self.index.add(self.vectors)

    def search(self, qvec: np.ndarray, k: int, min_score: float = 0.0) -> list[Hit]:
        if self.index is None or k <= 0:
            return []
        q = np.asarray(qvec, dtype=np.float32).reshape(1, -1)
        if not np.linalg.norm(q):
            return []
        scores, ids = self.index.search(_normalise(q), min(k, len(self.passages)))
        return [
            Hit(passage=self.passages[i], score=float(s))
            for s, i in zip(scores[0], ids[0])
            if i >= 0 and s >= min_score
        ]

    def save(self, directory: str) -> None:
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "passages.jsonl", "w") as f:
            for p in self.passages:
                f.write(p.model_dump_json() + "\n")
        np.save(d / "vectors.npy", self.vectors)

    @classmethod
    def load(cls, directory: str) -> "VectorStore":
        d = Path(directory)
        pf, vf = d / "passages.jsonl", d / "vectors.npy"
        for f in (pf, vf):
            if not f.exists():
                raise FileNotFoundError(f"Knowledge base file missing: {f}")
        passages = [Passage.model_validate(json.loads(line)) for line in pf.read_text().splitlines() if line.strip()]
        return cls(passages, np.load(vf))
