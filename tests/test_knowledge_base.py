import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import openai
import pytest

from src.knowledge_base import build_kb, chunk_text
from src.rag_pipeline import OpenAIEmbedder, RetrievalError, VectorStore
from src.schemas import Passage
from tests.conftest import FakeEmbedder

FIX = Path(__file__).parent / "fixtures"
URL = "https://sso.agc.gov.sg/Act/EA1968"
TITLE = "Employment Act 1968"


def _act():
    return (FIX / "mini_act.txt").read_text()


def test_chunk_fixture_three_passages():
    ps = chunk_text(_act(), TITLE, URL, "law")
    assert len(ps) == 3
    assert ps[1].citation == "Employment Act 1968 – 38. Hours of work"
    assert all(p.url == URL and p.kind == "law" and p.title == TITLE for p in ps)
    assert [p.id for p in ps] == ["employment-act-1968-0", "employment-act-1968-1", "employment-act-1968-2"]
    assert "preamble" not in " ".join(p.text for p in ps)


def test_long_body_split():
    body = "\n\n".join(f"Sentence number {i} is here. " * 20 for i in range(10))
    ps = chunk_text(f"# 1. Long\n{body}", TITLE, URL, "law")
    assert len(ps) > 1
    assert all(len(p.text) <= 1500 for p in ps)
    assert {p.citation for p in ps} == {"Employment Act 1968 – 1. Long"}
    assert len({p.id for p in ps}) == len(ps)


def test_long_single_paragraph_split_by_sentence():
    body = " ".join(f"Sentence number {i} is here." for i in range(200))
    ps = chunk_text(f"# 1. Long\n{body}", TITLE, URL, "guidance")
    assert len(ps) > 1 and all(len(p.text) <= 1500 for p in ps)


def test_empty_and_preamble_only():
    assert chunk_text("", TITLE, URL, "law") == []
    assert chunk_text("just a preamble\nno headings", TITLE, URL, "law") == []


def _store():
    ps = [Passage(id=str(i), kind="law", title="t", citation="c", url=None, page=None, text=str(i)) for i in range(3)]
    vecs = np.array([[1, 0], [0.9, 0.1], [0, 1]], dtype=np.float32)
    return VectorStore(ps, vecs), ps


def test_search_order_k_min_score():
    s, _ = _store()
    hits = s.search(np.array([1, 0], dtype=np.float32), k=2)
    assert [h.passage.id for h in hits] == ["0", "1"]
    assert hits[0].score >= hits[1].score
    hits = s.search(np.array([1, 0], dtype=np.float32), k=10, min_score=0.5)
    assert [h.passage.id for h in hits] == ["0", "1"]
    assert len(s.search(np.array([1, 0], dtype=np.float32), k=10)) == 3


def test_search_empty_and_zero():
    s, _ = _store()
    assert s.search(np.zeros(2, dtype=np.float32), k=3) == []
    empty = VectorStore([], np.zeros((0, 2), dtype=np.float32))
    assert empty.search(np.array([1, 0], dtype=np.float32), k=3) == []


def test_save_load_roundtrip(tmp_path):
    s, ps = _store()
    s.save(str(tmp_path))
    assert (tmp_path / "passages.jsonl").exists() and (tmp_path / "vectors.npy").exists()
    s2 = VectorStore.load(str(tmp_path))
    q = np.array([1, 0.2], dtype=np.float32)
    a, b = s.search(q, 3), s2.search(q, 3)
    assert [h.passage for h in a] == [h.passage for h in b]
    assert [h.score for h in a] == pytest.approx([h.score for h in b])


def test_load_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        VectorStore.load(str(tmp_path))
    s, ps = _store()
    with pytest.raises(ValueError):
        VectorStore(ps, np.zeros((2, 2), dtype=np.float32))
    s.save(str(tmp_path))
    np.save(tmp_path / "vectors.npy", np.zeros((2, 2), dtype=np.float32))
    with pytest.raises(ValueError):
        VectorStore.load(str(tmp_path))


def _manifest(tmp_path, entries):
    p = tmp_path / "sources.json"
    p.write_text(json.dumps(entries))
    return str(p)


def test_build_kb_finds_termination(tmp_path):
    (tmp_path / "act.txt").write_text(_act())
    m = _manifest(tmp_path, [{"file": str(tmp_path / "act.txt"), "kind": "law", "title": TITLE, "url": URL, "fetch": "manual"}])
    out = tmp_path / "out"
    n = build_kb(m, str(out), FakeEmbedder())
    assert n == 3
    store = VectorStore.load(str(out))
    emb = FakeEmbedder()
    hits = store.search(emb.embed(["notice"])[0], k=1)
    assert "Termination" in hits[0].passage.citation


def test_build_kb_missing_and_empty(tmp_path):
    m = _manifest(tmp_path, [{"file": str(tmp_path / "nope.txt"), "kind": "law", "title": TITLE, "url": URL, "fetch": "x"}])
    with pytest.raises(FileNotFoundError, match="nope.txt"):
        build_kb(m, str(tmp_path / "o"), FakeEmbedder())
    (tmp_path / "e.txt").write_text("no headings")
    m = _manifest(tmp_path, [{"file": str(tmp_path / "e.txt"), "kind": "law", "title": "Empty Src", "url": URL, "fetch": "x"}])
    with pytest.raises(ValueError, match="Empty Src"):
        build_kb(m, str(tmp_path / "o"), FakeEmbedder())


class _Client:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail
        self.embeddings = SimpleNamespace(create=self._create)

    def _create(self, model, input):
        if self.fail:
            raise openai.OpenAIError("boom")
        self.calls.append(list(input))
        return SimpleNamespace(data=[SimpleNamespace(embedding=[1.0, 2.0, 3.0, 4.0]) for _ in input])


def test_embedder_batches():
    c = _Client()
    out = OpenAIEmbedder(client=c).embed([f"t{i}" for i in range(250)])
    assert out.shape == (250, 4)
    assert [len(x) for x in c.calls] == [100, 100, 50]


def test_embedder_wraps_errors():
    with pytest.raises(RetrievalError):
        OpenAIEmbedder(client=_Client(fail=True)).embed(["a"])


def test_embedder_error_message_has_no_secrets():
    fake_key = "sk-" + "A1b2C3d4E5f6G7h8I9j0K1l2"
    phrase = "distinctive-confidential-phrase"

    class AuthErr(openai.OpenAIError):
        status_code = 401

    class Bad:
        embeddings = SimpleNamespace(
            create=lambda model, input: (_ for _ in ()).throw(AuthErr(f"Incorrect API key provided: {fake_key} {input}"))
        )

    with pytest.raises(RetrievalError) as ei:
        OpenAIEmbedder(client=Bad()).embed([phrase])
    msg = str(ei.value)
    assert fake_key not in msg and "sk-" not in msg and phrase not in msg
    assert "AuthErr" in msg and "401" in msg
    assert isinstance(ei.value.__cause__, AuthErr)


def test_build_kb_duplicate_ids(tmp_path):
    (tmp_path / "a.txt").write_text(_act())
    e = {"file": str(tmp_path / "a.txt"), "kind": "law", "title": TITLE, "url": URL, "fetch": "x"}
    m = _manifest(tmp_path, [e, dict(e)])
    with pytest.raises(ValueError, match="employment-act-1968-0"):
        build_kb(m, str(tmp_path / "o"), FakeEmbedder())
