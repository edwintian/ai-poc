import json
from pathlib import Path

import faiss
import numpy as np
import openai

from src.config import get_secret
from src.schemas import Evidence, Hit, Page, Passage, Source


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
            status = getattr(e, "status_code", None)
            detail = f" (HTTP {status})" if status else ""
            raise RetrievalError(f"Embedding request failed: {type(e).__name__}{detail}") from e
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
        with open(d / "passages.jsonl", "w", encoding="utf-8") as f:
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
        passages = [Passage.model_validate(json.loads(line)) for line in pf.read_text(encoding="utf-8").splitlines() if line.strip()]
        return cls(passages, np.load(vf))


CONTRACT_MAX_CHARS = 1200
_RETRIEVAL_FAILED = "Retrieval failed: could not embed the query."


def chunk_contract(pages: list[Page]) -> list[Passage]:
    from src.knowledge_base import _split_body

    out: list[Passage] = []
    for page in pages:
        body = page.text.strip()
        if not body:
            continue
        for i, piece in enumerate(_split_body(body, CONTRACT_MAX_CHARS)):
            out.append(Passage(
                id=f"contract-p{page.number}-{i}", kind="contract", title="Contract",
                citation=f"Contract, p. {page.number}", url=None, page=page.number, text=piece,
            ))
    return out


class RagPipeline:
    def __init__(self, kb: VectorStore, embedder):
        self.kb = kb  # read-only; never mutated (ADR 0009)
        self.embedder = embedder
        self.contract: VectorStore | None = None

    def index_contract(self, pages: list[Page]) -> None:
        passages = chunk_contract(pages)
        if not passages:
            self.contract = None
            return
        vectors = np.asarray(self.embedder.embed([p.text for p in passages]), dtype=np.float32)
        self.contract = VectorStore(passages, vectors)

    def clear_contract(self) -> None:
        self.contract = None

    def retrieve(
        self, query: str, k_contract: int = 3, k_official: int = 4, min_score: float = 0.25,
        min_score_contract: float | None = None, min_score_official: float | None = None,
    ) -> Evidence:
        if not query or not query.strip():
            return Evidence(contract=[], official=[])
        try:
            qvec = np.asarray(self.embedder.embed([query]), dtype=np.float32)[0]
        except RetrievalError:
            raise
        except Exception as e:
            raise RetrievalError(_RETRIEVAL_FAILED) from e
        mc = min_score if min_score_contract is None else min_score_contract
        mo = min_score if min_score_official is None else min_score_official
        contract = self.contract.search(qvec, k_contract, mc) if self.contract else []
        return Evidence(contract=contract, official=self.kb.search(qvec, k_official, mo))


def to_source(p: Passage) -> Source | None:
    if p.kind == "contract" or not p.url:
        return None
    return Source(title=p.title, url=p.url, citation=p.citation)


_KIND_LABEL = {"law": "Statute", "guidance": "MOM guidance", "contract": "Contract"}


def format_evidence(e: Evidence) -> str:
    def block(hits: list[Hit]) -> str:
        if not hits:
            return "(none)"
        return "\n\n".join(
            f"[{h.passage.id}] {_KIND_LABEL[h.passage.kind]} - {h.passage.citation}\n{h.passage.text}"
            for h in hits
        )

    return f"Contract passages:\n{block(e.contract)}\n\nOfficial sources:\n{block(e.official)}"


def resolve_sources(ids: list[str], e: Evidence) -> list[Source]:
    by_id = {h.passage.id: h.passage for h in e.official}
    out: list[Source] = []
    seen: set[str] = set()
    for i in ids:
        if i in seen or i not in by_id:
            continue
        seen.add(i)
        src = to_source(by_id[i])
        if src:
            out.append(src)
    return out


def filter_evidence(e: Evidence, ids: list[str]) -> Evidence:
    keep = set(ids)
    return Evidence(
        contract=[h for h in e.contract if h.passage.id in keep],
        official=[h for h in e.official if h.passage.id in keep],
    )
