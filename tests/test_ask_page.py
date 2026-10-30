from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src import llm as llm_mod
from src import qa
from src import rag_pipeline as rp
from src.contract_analyser import DISCLAIMER
from src.schemas import ChatTurn, Evidence, Hit, Passage

PAGE = str(Path(__file__).resolve().parent.parent / "pages" / "ask_contract.py")


def hit(kind, **kw):
    d = dict(id="i", kind=kind, title="T", citation="Cite *x*", url=None, page=None, text="txt")
    d.update(kw)
    return Hit(passage=Passage(**d), score=0.9)


class Pipe:
    def __init__(self, contract):
        self.contract = contract


@pytest.fixture
def env(monkeypatch):
    calls = []
    monkeypatch.setattr(llm_mod, "OpenAIClient", lambda: "llm")
    box = {"result": None}

    def fake_answer(question, history, pipeline, llm):
        calls.append((question, list(history), pipeline, llm))
        if isinstance(box["result"], Exception):
            raise box["result"]
        return box["result"]

    monkeypatch.setattr(qa, "answer", fake_answer)
    return type("Env", (), {"calls": calls, "box": box})


def make(contract="indexed", chat=None):
    at = AppTest.from_file(PAGE)
    at.session_state["pipeline"] = Pipe(contract)
    if chat is not None:
        at.session_state["chat"] = chat
    return at.run()


def ask(at, q="How much notice?"):
    at.chat_input[0].set_value(q).run()
    return at


def test_no_pipeline(env):
    at = AppTest.from_file(PAGE).run()
    assert any("Health Check" in i.value for i in at.info)
    assert len(at.chat_input) == 0


def test_no_contract(env):
    at = make(contract=None)
    assert any("Health Check" in i.value for i in at.info)
    assert len(at.chat_input) == 0


def test_disclaimer(env):
    at = make()
    assert any(DISCLAIMER in c.value for c in at.caption)
    assert len(at.chat_input) == 1


def test_answer_with_sources(env):
    env.box["result"] = ChatTurn(role="assistant", content="Give *1* month", evidence=Evidence(
        contract=[hit("contract", page=3, text="x" * 500)],
        official=[hit("guidance", url="https://mom.gov.sg/a", citation="MOM [notice]")]))
    at = ask(make())
    q, history, pipe, llm = env.calls[0]
    assert q == "How much notice?" and history == [] and llm == "llm" and pipe.contract
    chat = at.session_state["chat"]
    assert [t.role for t in chat] == ["user", "assistant"]
    assert chat[0].content == "How much notice?"
    msgs = [m.markdown[0].value for m in at.chat_message]
    assert msgs[0] == "How much notice?".replace("?", "\\?") or "notice" in msgs[0]
    assert "Give \\*1\\* month" in msgs[1]
    assert len(at.expander) == 1 and at.expander[0].label == "Sources"
    text = " ".join(m.value for m in at.expander[0].markdown)
    assert "Contract, p. 3" in text
    assert "x" * 300 in text and "x" * 400 not in text
    assert "[MOM \\[notice\\]](https://mom.gov.sg/a)" in text
    assert not at.exception


def test_history_before_question(env):
    prior = [ChatTurn(role="user", content="q0"), ChatTurn(role="assistant", content="a0")]
    env.box["result"] = ChatTurn(role="assistant", content="a1")
    at = ask(make(chat=prior), "q1")
    assert env.calls[0][1] == prior
    assert [t.content for t in at.session_state["chat"]] == ["q0", "a0", "q1", "a1"]
    assert len(at.chat_message) == 4


def test_refusal_no_expander(env):
    env.box["result"] = ChatTurn(role="assistant", content=qa.REFUSAL, evidence=Evidence(contract=[], official=[]))
    at = ask(make(), "weather?")
    assert len(at.expander) == 0
    assert qa.REFUSAL.replace(".", "\\.") in at.chat_message[1].markdown[0].value or \
        qa.REFUSAL in at.chat_message[1].markdown[0].value


@pytest.mark.parametrize("exc", [llm_mod.LLMError("secret-detail"), rp.RetrievalError("secret-detail")])
def test_error_history_unchanged(env, exc):
    env.box["result"] = exc
    at = ask(make())
    assert len(at.error) == 1 and "secret-detail" not in at.error[0].value
    assert at.session_state["chat"] == []
    assert len(at.chat_message) == 0
