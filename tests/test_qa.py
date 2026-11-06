import pytest

from src.llm import LLMError
from src.qa import MAX_HISTORY_TURNS, REFUSAL, answer
from src.rag_pipeline import RetrievalError, filter_evidence
from src.schemas import ChatTurn, Evidence, Hit, Passage, QAResponse


def hit(pid, kind, text, score=0.9):
    return Hit(passage=Passage(id=pid, kind=kind, title="T", citation=f"Cite {pid}",
                               url=None if kind == "contract" else "https://x.sg",
                               page=1 if kind == "contract" else None, text=text), score=score)


C1 = hit("contract-p1-0", "contract", "Either party gives one month notice.")
C2 = hit("contract-p2-0", "contract", "Salary is paid monthly.")
O1 = hit("ea-s10", "law", "Notice of termination statute text.")
O2 = hit("mom-1", "guidance", "MOM guidance on leave.")
FULL = Evidence(contract=[C1, C2], official=[O1, O2])
EMPTY = Evidence(contract=[], official=[])


class Pipe:
    def __init__(self, ev):
        self.ev, self.queries = ev, []

    def retrieve(self, query, **kw):
        self.queries.append(query)
        self.kw = kw
        if isinstance(self.ev, Exception):
            raise self.ev
        return self.ev


class LLM:
    def __init__(self, resp=None, exc=None):
        self.resp, self.exc, self.calls = resp, exc, []

    def structured(self, system, user, model_cls):
        self.calls.append((system, user, model_cls))
        if self.exc:
            raise self.exc
        return self.resp


def ok(ids, answerable=True, text="LLM ANSWER"):
    return QAResponse(answerable=answerable, answer=text, cited_ids=ids)


def test_no_evidence_refuses_without_llm():
    llm = LLM(ok([]))
    t = answer("What about notice?", [], Pipe(EMPTY), llm)
    assert t.role == "assistant" and t.content == REFUSAL and t.evidence == EMPTY
    assert llm.calls == []


@pytest.mark.parametrize("q", ["", "   \n"])
def test_blank_refuses(q):
    llm = LLM(ok([]))
    pipe = Pipe(FULL)
    t = answer(q, [], pipe, llm)
    assert t.content == REFUSAL and t.evidence == EMPTY and llm.calls == []


def test_prompt_contains_evidence_and_question():
    llm = LLM(ok([C1.passage.id]))
    answer("How much notice?", [], Pipe(FULL), llm)
    system, user, cls = llm.calls[0]
    assert cls is QAResponse
    for h in (C1, C2, O1, O2):
        assert h.passage.text in user and f"[{h.passage.id}]" in user
    assert "How much notice?" in user
    assert "untrusted" in system and "illegal" in system
    assert "does not mention it" in system  # absence questions are answerable, not refused


def test_history_truncated_and_content_only():
    hist = [ChatTurn(role="user" if i % 2 == 0 else "assistant", content=f"turn-{i}", evidence=FULL)
            for i in range(10)]
    llm = LLM(ok([C1.passage.id]))
    pipe = Pipe(FULL)
    answer("current q", hist, pipe, llm)
    user = llm.calls[0][1]
    assert MAX_HISTORY_TURNS == 6
    for i in range(4):
        assert f"turn-{i}\n" not in user + "\n" and f"turn-{i}" not in user
    for i in range(4, 10):
        assert f"turn-{i}" in user
    assert "User: turn-4" in user and "Assistant: turn-5" in user
    assert user.count(C1.passage.text) == 1  # evidence only once, from current retrieval
    assert pipe.queries == ["current q", "turn-8\ncurrent q"]  # also searched with last user turn


@pytest.mark.parametrize("exc", [LLMError("x"), RetrievalError("y")])
def test_errors_propagate(exc):
    with pytest.raises(type(exc)):
        answer("q", [], Pipe(FULL), LLM(exc=exc))
    with pytest.raises(type(exc)):
        answer("q", [], Pipe(exc), LLM(ok([])))


def test_not_answerable_refuses():
    t = answer("q", [], Pipe(FULL), LLM(ok([C1.passage.id], answerable=False)))
    assert t.content == REFUSAL and "LLM ANSWER" not in t.content and t.evidence == EMPTY


def test_unknown_citations_refuse():
    t = answer("q", [], Pipe(FULL), LLM(ok(["made-up"])))
    assert t.content == REFUSAL and t.evidence == EMPTY


def test_answer_with_cited_evidence_only():
    t = answer("q", [], Pipe(FULL), LLM(ok([O1.passage.id, C1.passage.id, "bogus"])))
    assert t.role == "assistant" and t.content == "LLM ANSWER"
    assert [h.passage.id for h in t.evidence.contract] == [C1.passage.id]
    assert [h.passage.id for h in t.evidence.official] == [O1.passage.id]


def test_filter_evidence_drops_unknown_keeps_order():
    out = filter_evidence(FULL, ["mom-1", "nope", "contract-p2-0", "contract-p1-0", "ea-s10"])
    assert [h.passage.id for h in out.contract] == ["contract-p1-0", "contract-p2-0"]
    assert [h.passage.id for h in out.official] == ["ea-s10", "mom-1"]
    assert filter_evidence(FULL, []) == EMPTY


def test_answer_passes_qa_thresholds():
    from src.qa import QA_MIN_SCORE_CONTRACT, QA_MIN_SCORE_OFFICIAL
    pipe = Pipe(FULL)
    answer("q", [], pipe, LLM(ok([C1.passage.id])))
    assert pipe.kw == {"min_score_contract": QA_MIN_SCORE_CONTRACT,
                       "min_score_official": QA_MIN_SCORE_OFFICIAL}
    assert (QA_MIN_SCORE_CONTRACT, QA_MIN_SCORE_OFFICIAL) == (0.27, 0.40)


class FollowUpPipe:
    """Returns nothing for the bare follow-up, evidence only when the earlier question is included."""
    def __init__(self):
        self.queries = []

    def retrieve(self, query, **kw):
        self.queries.append(query)
        return FULL if "childcare" in query else EMPTY


def test_follow_up_retrieves_with_previous_question():
    hist = [ChatTurn(role="user", content="How much childcare leave?"),
            ChatTurn(role="assistant", content="2 days per relevant period.")]
    pipe = FollowUpPipe()
    t = answer("what is a relevant period?", hist, pipe, LLM(ok([O1.passage.id])))
    assert t.content == "LLM ANSWER" and [h.passage.id for h in t.evidence.official] == ["ea-s10"]
    assert pipe.queries == ["what is a relevant period?",
                            "How much childcare leave?\nwhat is a relevant period?"]


def test_first_question_retrieves_once():
    pipe = Pipe(FULL)
    answer("q", [], pipe, LLM(ok([C1.passage.id])))
    assert pipe.queries == ["q"]


def test_merge_dedupes_keeps_best_score():
    from src.qa import _merge
    a = Evidence(contract=[hit("c", "contract", "x", 0.3)], official=[hit("o", "law", "y", 0.5)])
    b = Evidence(contract=[hit("c", "contract", "x", 0.6)], official=[hit("p", "law", "z", 0.7)])
    m = _merge(a, b)
    assert [(h.passage.id, h.score) for h in m.contract] == [("c", 0.6)]
    assert [h.passage.id for h in m.official] == ["p", "o"]
