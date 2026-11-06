import logging
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from src import contract_analyser as ca
from src import document_parser as dp
from src import llm as llm_mod
from src import rag_pipeline as rp
from src.schemas import Finding, Page, Report, Source, TERM_KEYS

PAGE = str(Path(__file__).resolve().parent.parent / "pages" / "health_check.py")
SECRET = "Zanzibar clause 7 unique phrase"
PDF = ("c.pdf", b"%PDF-fake", "application/pdf")


class FakeEmbedder:
    pass


class FakeBar:
    calls: list = []

    def __init__(self, value, text=None):
        FakeBar.calls.append(("init", value, text))

    def progress(self, value, text=None):
        FakeBar.calls.append(("progress", value, text))

    def empty(self):
        FakeBar.calls.append(("empty",))


def make_report():
    statuses = ["Consistent", "Needs Attention", "Unable to Assess"]
    findings = []
    for i, key in enumerate(TERM_KEYS):
        found = i != 2
        findings.append(Finding(
            term=key, status=statuses[i % 3],
            wording=f"wording {i}" if found else None, page=i + 1 if found else None,
            explanation=f"explain {i}", reason=f"reason {i}",
            sources=[Source(title="t", url=f"https://example.com/{i}", citation=f"Cite {i}")],
            question="Ask HR?" if i == 0 else None))
    return Report(findings=findings, disclaimer="DISCLAIMER TEXT")


@pytest.fixture
def env(monkeypatch):
    st.cache_resource.clear()
    kb = object()
    calls = []
    monkeypatch.setattr(rp.VectorStore, "load", classmethod(lambda cls, d: kb))
    monkeypatch.setattr(rp, "OpenAIEmbedder", FakeEmbedder)
    monkeypatch.setattr(llm_mod, "OpenAIClient", lambda: object())
    monkeypatch.setattr(dp, "parse_pdf", lambda data: [Page(number=1, text=SECRET)])

    def fake_analyse(pages, pipeline, llm, progress=None):
        calls.append((pages, progress))
        pipeline.contract = "indexed"
        if progress:
            progress(3, 11)
        return make_report()

    monkeypatch.setattr(ca, "analyse", fake_analyse)
    FakeBar.calls = []
    monkeypatch.setattr(st, "progress", FakeBar)
    return type("Env", (), {"kb": kb, "calls": calls, "mp": monkeypatch})


def run_upload(at=None):
    at = at or AppTest.from_file(PAGE).run()
    at.file_uploader[0].set_value(PDF)
    at.run()
    return at


def analyze(at):
    at.button(key="analyze").click()
    return at.run()


def test_widgets(env):
    at = AppTest.from_file(PAGE).run()
    assert at.file_uploader[0].allowed_type == [".pdf"]
    assert len(at.selectbox) == 0 and len(at.number_input) == 0  # no category/salary inputs
    assert any("OpenAI" in m.value for m in list(at.info) + list(at.caption))
    assert at.button(key="analyze").disabled


def test_analyze_enabled_after_upload(env):
    at = run_upload()
    assert not at.button(key="analyze").disabled


def test_analyze_calls_once_stores_report(env):
    at = run_upload()
    at = analyze(at)
    assert len(env.calls) == 1 and callable(env.calls[0][1])
    assert len(at.session_state["report"].findings) == 11
    assert ("progress", 3 / 11, "Assessing term 3 of 11") in FakeBar.calls
    at.run()  # a rerun must not re-analyse
    assert len(env.calls) == 1
    assert at.session_state["report"] is not None
    assert not at.exception


@pytest.mark.parametrize("exc,expect", [
    (dp.UnreadableDocument("Scanned PDF unsupported."), "Scanned PDF unsupported."),
    (ca.NotAContract("x"), "doesn't look like an employment contract"),
    (llm_mod.LLMError("secret-detail"), "unavailable right now"),
    (rp.RetrievalError("secret-detail"), "unavailable right now"),
])
def test_errors(env, exc, expect):
    def boom(*a, **k):
        raise exc
    env.mp.setattr(ca, "analyse", boom)
    env.mp.setattr(dp, "parse_pdf", lambda d: (_ for _ in ()).throw(exc)
                   if isinstance(exc, dp.UnreadableDocument) else [Page(number=1, text="x")])
    at = analyze(run_upload())
    assert len(at.error) == 1
    assert expect in at.error[0].value
    assert "secret-detail" not in at.error[0].value
    assert at.session_state["report"] is None


@pytest.mark.parametrize("exc", [FileNotFoundError("x"), ValueError("y")])
def test_missing_kb(env, exc):
    def bad(cls, d):
        raise exc
    env.mp.setattr(rp.VectorStore, "load", classmethod(bad))
    at = analyze(run_upload())
    assert len(at.error) == 1 and "python scripts/build_kb.py" in at.error[0].value
    assert at.session_state["report"] is None
    assert not env.calls


def test_report_rendering(env):
    at = analyze(run_upload())
    df = at.table[0].value
    assert list(df.columns) == ["Term", "Status", "Wording"]
    assert len(df) == 11
    assert set(df["Status"]) == {"Consistent", "Needs Attention", "Unable to Assess"}
    assert df["Wording"][2] == "Not found in contract"
    assert len(at.expander) == 11
    assert "Salary payment" in at.expander[0].label and "Consistent" in at.expander[0].label
    text0 = " ".join(m.value for m in at.expander[0].markdown)
    assert "wording 0" in text0 and "(page 1)" in text0 and "explain 0" in text0
    assert "reason 0" in text0 and "[Cite 0](https://example.com/0)" in text0
    assert "Ask HR?" in text0
    text2 = " ".join(m.value for m in at.expander[2].markdown)
    assert "Not found in contract" in text2
    assert any("DISCLAIMER TEXT" in m.value for m in list(at.markdown) + list(at.caption))


def test_clear(env):
    at = analyze(run_upload())
    at.session_state["chat"] = [object()]
    at.button(key="clear").click()
    at.run()
    assert at.session_state["report"] is None
    assert at.session_state["pipeline"].contract is None
    assert not at.session_state["chat"]
    assert len(at.expander) == 0
    assert at.file_uploader[0].value is None
    assert at.button(key="analyze").disabled


def test_no_contract_text_in_logs(env, capsys, caplog):
    caplog.set_level(logging.DEBUG)
    analyze(run_upload())
    out = capsys.readouterr()
    assert SECRET not in out.out + out.err + caplog.text


def test_bytes_not_in_session_state(env):
    at = analyze(run_upload())
    for k in list(at.session_state.keys()):
        v = at.session_state[k]
        assert not isinstance(v, (bytes, bytearray)), k
    assert "pages" not in at.session_state


def test_pipeline_is_per_session_with_shared_kb(env):
    at = analyze(run_upload())
    pipe = at.session_state["pipeline"]
    assert pipe is not env.kb and pipe.kb is env.kb


def test_second_session_isolated(env):
    def make(tag):
        def fake(pages, pipeline, llm, progress=None):
            pipeline.contract = tag
            r = make_report()
            r.disclaimer = tag
            return r
        return fake
    env.mp.setattr(ca, "analyse", make("one"))
    first = analyze(run_upload())
    env.mp.setattr(ca, "analyse", make("two"))
    second = analyze(run_upload())
    p1, p2 = first.session_state["pipeline"], second.session_state["pipeline"]
    assert p1 is not p2 and p1.kb is env.kb and p2.kb is env.kb
    assert first.session_state["report"].disclaimer == "one"
    assert second.session_state["report"].disclaimer == "two"
    second.button(key="clear").click()
    second.run()
    assert second.session_state["report"] is None and p2.contract is None
    assert first.session_state["report"].disclaimer == "one" and p1.contract == "one"


def test_untrusted_text_is_escaped(env):
    evil = "![x](https://evil.example/p.png) **bold** S$2,000 and S$300"

    def fake(pages, pipeline, llm, progress=None):
        r = make_report()
        r.findings[0].explanation = evil
        r.findings[0].wording = evil
        r.findings[0].reason = evil
        r.findings[0].question = evil
        return r

    env.mp.setattr(ca, "analyse", fake)
    at = analyze(run_upload())
    assert len(at.get("imgs")) == 0
    body = " ".join(m.value for m in at.expander[0].markdown)
    assert "\\!\\[x\\]\\(https://evil" in body
    assert "\\*\\*bold\\*\\*" in body
    assert "S\\$2,000" in body and "S\\$300" in body
    assert body.count(evil) == 0


def test_failed_analyze_leaves_nothing(env):
    at = analyze(run_upload())
    assert at.session_state["report"] is not None

    def fail(pages, pipeline, llm, progress=None):
        pipeline.contract = "indexed"
        raise llm_mod.LLMError("x")

    env.mp.setattr(ca, "analyse", fail)
    at.session_state["chat"] = ["old"]
    at = analyze(at)
    assert at.session_state["report"] is None
    assert at.session_state["pipeline"].contract is None
    assert not at.session_state["chat"]
    assert len(at.error) == 1


def test_clear_visible_when_only_contract_indexed(env):
    at = AppTest.from_file(PAGE).run()
    assert [b.key for b in at.button] == ["analyze"]
    at = AppTest.from_file(PAGE)
    at.session_state["pipeline"] = rp.RagPipeline(env.kb, FakeEmbedder())
    at.session_state["pipeline"].contract = "indexed"
    at.run()
    assert at.session_state["report"] is None
    assert [b.key for b in at.button] == ["analyze", "clear"]


def test_progress_bar_emptied_on_error(env):
    def fail(pages, pipeline, llm, progress=None):
        raise llm_mod.LLMError("x")

    env.mp.setattr(ca, "analyse", fail)
    analyze(run_upload())
    assert FakeBar.calls[-1] == ("empty",)
