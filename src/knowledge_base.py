import json
import re
from pathlib import Path
from typing import Literal

import numpy as np

from src.schemas import Passage

MAX_CHARS = 1500


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _pack(pieces: list[str], sep: str, max_chars: int = MAX_CHARS) -> list[str]:
    out: list[str] = []
    cur = ""
    for p in pieces:
        cand = f"{cur}{sep}{p}" if cur else p
        if len(cand) <= max_chars:
            cur = cand
        else:
            if cur:
                out.append(cur)
            cur = p
    if cur:
        out.append(cur)
    return out


def _split_body(body: str, max_chars: int = MAX_CHARS) -> list[str]:
    if len(body) <= max_chars:
        return [body]
    out: list[str] = []
    for chunk in _pack([p for p in re.split(r"\n\s*\n", body) if p.strip()], "\n\n", max_chars):
        if len(chunk) <= max_chars:
            out.append(chunk)
            continue
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", chunk) if s]
        for sub in _pack(sentences, " ", max_chars):
            while len(sub) > max_chars:  # last resort: a single oversize sentence
                out.append(sub[:max_chars])
                sub = sub[max_chars:]
            if sub:
                out.append(sub)
    return out


def chunk_text(text: str, title: str, url: str, kind: Literal["law", "guidance"]) -> list[Passage]:
    sections: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        if line.startswith("#"):
            sections.append((line.lstrip("#").strip(), []))
        elif sections:
            sections[-1][1].append(line)
    passages: list[Passage] = []
    for heading, lines in sections:
        body = "\n".join(lines).strip()
        if not body:
            continue
        for piece in _split_body(body):
            passages.append(Passage(
                id=f"{slug(title)}-{len(passages)}", kind=kind, title=title,
                citation=f"{title} – {heading}", url=url, page=None, text=piece,
            ))
    return passages


def build_kb(manifest_path: str, out_dir: str, embedder) -> int:
    from src.rag_pipeline import VectorStore

    entries = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    passages: list[Passage] = []
    for e in entries:
        f = Path(e["file"])
        if not f.is_absolute() and not f.exists():
            alt = Path(manifest_path).parent / f
            f = alt if alt.exists() else f
        if not f.exists():
            raise FileNotFoundError(f"Knowledge base source file not found: {e['file']}")
        ps = chunk_text(f.read_text(encoding="utf-8"), e["title"], e["url"], e["kind"])
        if not ps:
            raise ValueError(f"Source yielded no passages: {e['title']} ({e['file']})")
        passages.extend(ps)
    seen: dict[str, str] = {}
    for p in passages:
        if p.id in seen:
            raise ValueError(f"Duplicate passage id {p.id!r} (sources: {seen[p.id]!r} and {p.title!r})")
        seen[p.id] = p.title
    vectors = np.asarray(embedder.embed([p.text for p in passages]), dtype=np.float32)
    VectorStore(passages, vectors).save(out_dir)
    return len(passages)
