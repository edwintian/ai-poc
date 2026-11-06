from src.contract_analyser import UNTRUSTED
from src.llm import complete_structured
from src.rag_pipeline import filter_evidence, format_evidence
from src.schemas import ChatTurn, Evidence, Hit, QAResponse

REFUSAL = (
    "I can't answer that from your contract and the official sources I have. Try rephrasing, "
    "or ask about a specific term such as notice, leave, hours, salary or deductions."
)
MAX_HISTORY_TURNS = 6
# Per-list thresholds from the 2026-10-30 real-embedding check on varied_notice_leave.pdf:
# on-topic questions scored official >= 0.465 and contract >= 0.295; off-topic questions scored
# official <= 0.361 and contract <= 0.248. No single value separates both lists.
QA_MIN_SCORE_CONTRACT = 0.27
QA_MIN_SCORE_OFFICIAL = 0.40

QA_SYSTEM = f"""You answer follow-up questions about a Singapore employment contract, using only the
passages shown: contract passages and official sources (the Employment Act and MOM guidance).
{UNTRUSTED}

Rules:
- Answer in concise, plain English.
- Say what you cannot determine from the passages.
- Distinguish what the contract says from what the statute or MOM guidance says.
- Cite only ids shown in the evidence (contract or official passages) in `cited_ids`.
- A question about whether something is required or included (for example a bonus, 13th-month pay
  or a pay increment) is answerable when the passages are on a related topic, even if none of them
  mentions it: say what the contract says or that it does not mention it, and what the official
  sources shown say or that they do not require it. Cite the passages you relied on. Do not claim
  more than the passages support: say the sources shown do not require it, not that no law does.
- Set `answerable` to false only when the passages are unrelated to the question's topic.
- Never call anything "illegal"; describe it as consistent with or different from the sources.
- Earlier conversation turns are context only, not evidence.
"""


def _empty() -> Evidence:
    return Evidence(contract=[], official=[])


def _refusal() -> ChatTurn:
    return ChatTurn(role="assistant", content=REFUSAL, evidence=_empty())


def _merge(a: Evidence, b: Evidence) -> Evidence:
    """Union by passage id, keeping each passage's best score, highest first."""
    def union(x: list[Hit], y: list[Hit]) -> list[Hit]:
        best: dict[str, Hit] = {}
        for h in x + y:
            if h.passage.id not in best or h.score > best[h.passage.id].score:
                best[h.passage.id] = h
        return sorted(best.values(), key=lambda h: h.score, reverse=True)

    return Evidence(contract=union(a.contract, b.contract), official=union(a.official, b.official))


def _retrieve(question: str, history: list[ChatTurn], pipeline) -> Evidence:
    """Search on the question; for a follow-up, also on the previous user question plus this one.

    A follow-up such as "what do you mean by relevant period?" has no topic words of its own, so
    on its own it scores below the thresholds and would be refused before the LLM sees it.
    """
    kw = {"min_score_contract": QA_MIN_SCORE_CONTRACT, "min_score_official": QA_MIN_SCORE_OFFICIAL}
    evidence = pipeline.retrieve(question, **kw)
    previous = next((t.content for t in reversed(history) if t.role == "user"), None)
    if previous:
        evidence = _merge(evidence, pipeline.retrieve(f"{previous}\n{question}", **kw))
    return evidence


def answer(question: str, history: list[ChatTurn], pipeline, llm) -> ChatTurn:
    if not question or not question.strip():
        return _refusal()
    evidence = _retrieve(question, history, pipeline)
    if not evidence.contract and not evidence.official:
        return _refusal()
    turns = history[-MAX_HISTORY_TURNS:]
    convo = "\n".join(f"{'User' if t.role == 'user' else 'Assistant'}: {t.content}" for t in turns)
    user = (
        (f"Conversation so far:\n{convo}\n\n" if convo else "")
        + f"{format_evidence(evidence)}\n\nQuestion: {question}"
    )
    resp = complete_structured(llm, QA_SYSTEM, user, QAResponse)
    if not resp.answerable:
        return _refusal()
    cited = filter_evidence(evidence, resp.cited_ids)
    if not cited.contract and not cited.official:
        return _refusal()
    return ChatTurn(role="assistant", content=resp.answer, evidence=cited)
