from typing import Literal

from pydantic import BaseModel

Status = Literal["Consistent", "Needs Attention", "Unable to Assess"]
TERM_KEYS = [
    "salary_payment", "working_hours", "overtime", "annual_leave", "sick_leave",
    "probation", "notice_period", "deductions", "termination", "confidentiality",
    "non_compete",
]


class Page(BaseModel):
    number: int
    text: str


class Passage(BaseModel):
    id: str
    kind: Literal["law", "guidance", "contract"]
    title: str
    citation: str
    url: str | None
    page: int | None
    text: str


class Hit(BaseModel):
    passage: Passage
    score: float


class Evidence(BaseModel):
    contract: list[Hit]
    official: list[Hit]


class Source(BaseModel):
    title: str
    url: str
    citation: str


class ExtractedTerm(BaseModel):
    key: str
    found: bool
    wording: str | None
    page: int | None
    weekly_hours: float | None
    overtime_multiplier: float | None
    annual_leave_days: float | None


class ContractTerms(BaseModel):
    is_employment_contract: bool
    terms: list[ExtractedTerm]  # list, not dict: structured outputs disallow free keys


class TermAssessment(BaseModel):
    status: Status
    explanation: str
    reason: str
    question: str | None
    source_ids: list[str]


class RuleResult(BaseModel):
    term: str
    status: Status
    reason: str
    source_ids: list[str]


class Finding(BaseModel):
    term: str
    status: Status
    wording: str | None
    page: int | None
    explanation: str
    reason: str
    sources: list[Source]
    question: str | None


class Report(BaseModel):
    findings: list[Finding]
    disclaimer: str


class QAResponse(BaseModel):
    answerable: bool
    answer: str
    cited_ids: list[str]


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    evidence: Evidence | None = None
