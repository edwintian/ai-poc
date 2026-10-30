from src.contract_analyser import UNTRUSTED
from src.llm import complete_structured
from src.rag_pipeline import filter_evidence, format_evidence
from src.schemas import ChatTurn, Evidence, QAResponse

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
- If the shown passages do not answer the question, set `answerable` to false.
- Never call anything "illegal"; describe it as consistent with or different from the sources.
- Earlier conversation turns are context only, not evidence.
"""


def _empty() -> Evidence:
    return Evidence(contract=[], official=[])


def _refusal() -> ChatTurn:
    return ChatTurn(role="assistant", content=REFUSAL, evidence=_empty())


def answer(question: str, history: list[ChatTurn], pipeline, llm) -> ChatTurn:
    if not question or not question.strip():
        return _refusal()
    evidence = pipeline.retrieve(
        question, min_score_contract=QA_MIN_SCORE_CONTRACT, min_score_official=QA_MIN_SCORE_OFFICIAL
    )
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
