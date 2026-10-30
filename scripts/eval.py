"""Accuracy eval over the sample contracts (ADR 0011): python scripts/eval.py (from repo root).

Needs OPENAI_API_KEY and the built knowledge base. Costs a few cents per run.
"""
import json
import sys
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sample_contracts"))

from src.schemas import TERM_KEYS, EmploymentContext, Report  # noqa: E402


class EvalScore(BaseModel):
    found_correct: int
    status_correct: int
    unsafe_consistent: int
    total: int


def _allowed(status) -> list[str]:
    return list(status) if isinstance(status, list) else [status]


def _compare(expected: dict, reports: dict[str, Report]) -> list[tuple[str, str, bool, bool, str, str]]:
    """Per (sample, term): (sample, term, found_ok, status_ok, expected_text, actual_text)."""
    rows = []
    for name, entry in expected.items():
        by_term = {f.term: f for f in reports[name].findings}
        for key in TERM_KEYS:
            e, f = entry[key], by_term[key]
            got_found = f.wording is not None
            found_ok = e["found"] == got_found and (not e["found"] or e["page"] == f.page)
            allowed = _allowed(e["status"])
            exp_txt = f"{'found p' + str(e['page']) if e['found'] else 'not found'} / {' | '.join(allowed)}"
            act_txt = f"{'found p' + str(f.page) if got_found else 'not found'} / {f.status}"
            rows.append((name, key, found_ok, f.status in allowed, exp_txt, act_txt))
    return rows


def _unsafe(expected: dict, name: str, key: str, status: str) -> bool:
    return status == "Consistent" and "Consistent" not in _allowed(expected[name][key]["status"])


def score(expected: dict, reports: dict[str, Report]) -> EvalScore:
    rows = _compare(expected, reports)
    unsafe = sum(
        _unsafe(expected, n, k, next(f.status for f in reports[n].findings if f.term == k))
        for n, k, *_ in rows
    )
    return EvalScore(found_correct=sum(r[2] for r in rows), status_correct=sum(r[3] for r in rows),
                     unsafe_consistent=unsafe, total=len(rows))


def main(analyse_fn: Callable | None = None, pipeline=None, llm=None, expected: dict | None = None,
         samples_dir: Path | None = None) -> int:
    if analyse_fn is None:
        from src.contract_analyser import analyse as analyse_fn
    samples_dir = samples_dir or ROOT / "sample_contracts"
    if expected is None:
        expected = json.loads((samples_dir / "expected.json").read_text(encoding="utf-8"))
    if pipeline is None:
        from src.rag_pipeline import OpenAIEmbedder, RagPipeline, VectorStore
        pipeline = RagPipeline(VectorStore.load(str(ROOT / "data" / "knowledge_base")), OpenAIEmbedder())
    if llm is None:
        from src.llm import OpenAIClient
        llm = OpenAIClient()
    from src.document_parser import parse_pdf

    reports: dict[str, Report] = {}
    for name, entry in expected.items():
        pages = parse_pdf((samples_dir / f"{name}.pdf").read_bytes())
        ctx = EmploymentContext(**entry["_context"])
        reports[name] = analyse_fn(pages, ctx, pipeline, llm)

    rows = _compare(expected, reports)
    status_of = {(n, f.term): f.status for n, r in reports.items() for f in r.findings}
    print(f"{'sample':<22}{'term':<17}{'expected':<44}actual")
    for name, key, found_ok, status_ok, exp_txt, act_txt in rows:
        unsafe = _unsafe(expected, name, key, status_of[(name, key)])
        if not (found_ok and status_ok) or unsafe:
            print(f"{name:<22}{key:<17}{exp_txt:<44}{act_txt}{'  UNSAFE CONSISTENT' if unsafe else ''}")
    s = score(expected, reports)
    print(f"\nfound correct:     {s.found_correct}/{s.total}")
    print(f"status correct:    {s.status_correct}/{s.total}")
    print(f"unsafe Consistent: {s.unsafe_consistent}")
    return 1 if s.unsafe_consistent > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
