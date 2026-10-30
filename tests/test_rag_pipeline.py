from pathlib import Path

import pytest

from conftest import FakeEmbedder
from src.knowledge_base import chunk_text
from src.rag_pipeline import (
    RagPipeline, RetrievalError, VectorStore, chunk_contract, format_evidence,
    resolve_sources, to_source,
)
from src.schemas import Evidence, Hit, Page, Passage

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture
def kb():
    ps = chunk_text((FIX / "mini_act.txt").read_text(), "Employment Act 1968",
                    "https://sso.agc.gov.sg/Act/EA1968", "law")
    return VectorStore(ps, FakeEmbedder().embed([p.text for p in ps]))


PAGES = [
    Page(number=1, text="The employee shall receive salary monthly."),
    Page(number=2, text="Either party may end this agreement with one month notice."),
]


def test_chunk_contract_metadata():
    ps = chunk_contract(PAGES)
    assert [p.page for p in ps] == [1, 2]
    assert ps[1].citation == "Contract, p. 2"
    assert all(p.kind == "contract" and p.url is None and p.title == "Contract" for p in ps)
    assert len({p.id for p in ps}) == len(ps)
    assert ps[0].id == "contract-p1-0"


def test_chunk_contract_splits_long_pages_and_skips_blank():
    long = "\n\n".join(f"Paragraph {i}. " + "word " * 100 for i in range(10))
    ps = chunk_contract([Page(number=3, text=long), Page(number=4, text="   ")])
    assert len(ps) > 1
    assert all(len(p.text) <= 1200 and p.page == 3 for p in ps)
    assert len({p.id for p in ps}) == len(ps)
    assert chunk_contract([Page(number=1, text="x" * 3000)])[0].text == "x" * 1200


def test_retrieve_separates_contract_and_official(kb):
    rp = RagPipeline(kb, FakeEmbedder())
    rp.index_contract(PAGES)
    e = rp.retrieve("notice")
    assert [h.passage.page for h in e.contract] == [2]
    assert all(h.passage.kind == "contract" for h in e.contract)
    assert e.official and "Termination" in e.official[0].passage.citation
    assert all(h.passage.kind == "law" for h in e.official)


def test_min_score_filters(kb):
    rp = RagPipeline(kb, FakeEmbedder())
    rp.index_contract(PAGES)
    e = rp.retrieve("notice salary", min_score=0.99)
    assert e.contract == [] and e.official == []


def test_blank_query_no_embedder_call(kb):
    class Boom:
        def embed(self, texts):
            raise AssertionError("called")
    rp = RagPipeline(kb, Boom())
    assert rp.retrieve("  \n") == Evidence(contract=[], official=[])


def test_embedder_errors(kb):
    class Re:
        def embed(self, t):
            raise RetrievalError("x")

    class Other:
        def embed(self, t):
            raise RuntimeError("sk-secret")

    with pytest.raises(RetrievalError):
        RagPipeline(kb, Re()).retrieve("notice")
    with pytest.raises(RetrievalError) as ei:
        RagPipeline(kb, Other()).retrieve("notice")
    assert "sk-secret" not in str(ei.value)


def test_no_contract_and_clear(kb):
    rp = RagPipeline(kb, FakeEmbedder())
    assert rp.retrieve("notice").contract == []
    rp.index_contract(PAGES)
    assert rp.retrieve("notice").contract
    rp.clear_contract()
    assert rp.retrieve("notice").contract == []
    assert rp.retrieve("notice").official


def test_pipelines_independent(kb):
    n = len(kb.passages)
    a, b = RagPipeline(kb, FakeEmbedder()), RagPipeline(kb, FakeEmbedder())
    a.index_contract(PAGES)
    assert a.retrieve("notice").contract
    assert b.retrieve("notice").contract == []
    assert len(kb.passages) == n
    a.index_contract([Page(number=9, text="overtime")])
    assert [h.passage.page for h in a.retrieve("notice overtime", min_score=0.1).contract] == [9]


def _ev(kb):
    rp = RagPipeline(kb, FakeEmbedder())
    rp.index_contract(PAGES)
    return rp.retrieve("notice")


def test_to_source(kb):
    e = _ev(kb)
    assert to_source(e.contract[0].passage) is None
    s = to_source(e.official[0].passage)
    assert s.url == "https://sso.agc.gov.sg/Act/EA1968" and s.title == "Employment Act 1968"
    g = Passage(id="g", kind="guidance", title="t", citation="c", url=None, page=None, text="x")
    assert to_source(g) is None


def test_format_evidence(kb):
    e = _ev(kb)
    t = format_evidence(e)
    for h in e.contract + e.official:
        assert h.passage.id in t and h.passage.citation in t
    assert "Statute" in t and "Contract passages" in t and "Official sources" in t
    assert t.index("Contract passages") < t.index("Official sources")
    assert "(none)" in format_evidence(Evidence(contract=[], official=[]))
    only = format_evidence(Evidence(contract=[], official=e.official))
    assert "(none)" in only and "Statute" in only


def test_format_labels_guidance():
    g = Passage(id="g1", kind="guidance", title="MOM", citation="MOM – Leave", url="u", page=None, text="body")
    assert "MOM guidance" in format_evidence(Evidence(contract=[], official=[Hit(passage=g, score=1)]))


def test_resolve_sources(kb):
    e = _ev(kb)
    oid = e.official[0].passage.id
    out = resolve_sources(["nope", e.contract[0].passage.id, oid, oid], e)
    assert len(out) == 1 and out[0].citation == e.official[0].passage.citation
    assert resolve_sources([], e) == []
