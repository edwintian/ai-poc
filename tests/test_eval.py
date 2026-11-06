import json
import re
from pathlib import Path

import pytest

from scripts import eval as ev
from sample_contracts.make_samples import SAMPLES
from src.schemas import TERM_KEYS, Finding, Report

ROOT = Path(__file__).resolve().parent.parent
EXPECTED = json.loads((ROOT / "sample_contracts" / "expected.json").read_text())
STATUSES = {"Consistent", "Needs Attention", "Unable to Assess"}


def _ws(s):
    return re.sub(r"\s+", " ", s)


def _statuses(v):
    return set(v) if isinstance(v, list) else {v}


def test_expected_shape():
    assert set(EXPECTED) == set(SAMPLES)
    for name, entry in EXPECTED.items():
        assert set(entry) == set(TERM_KEYS)
        for key in TERM_KEYS:
            e = entry[key]
            assert _statuses(e["status"]) <= STATUSES and e["status"]
            assert e["found"] == (e["page"] is not None)
            if key in ("confidentiality", "non_compete"):
                assert e["status"] == "Unable to Assess"


def test_phrases_in_pages():
    for name, entry in EXPECTED.items():
        for key in TERM_KEYS:
            e = entry[key]
            if e["found"]:
                assert _ws(e["phrase"]) in _ws(SAMPLES[name][e["page"] - 1]), (name, key)


def _finding(term, status, wording="w", page=1):
    return Finding(term=term, status=status, wording=wording if page else None, page=page,
                   explanation="", reason="", sources=[], question=None)


def _report(**over):
    fs = []
    for k in TERM_KEYS:
        fs.append(over.get(k) or _finding(k, "Unable to Assess", None, None))
    return Report(findings=fs, disclaimer="")


def _exp(**over):
    d = {k: {"found": False, "page": None, "status": "Unable to Assess"} for k in TERM_KEYS}
    d.update(over)
    return {"s": d}


def test_score_perfect_and_total():
    s = ev.score(_exp(), {"s": _report()})
    assert (s.found_correct, s.status_correct, s.unsafe_consistent, s.total) == (11, 11, 0, 11)


def test_score_found_requires_page_and_list_status():
    exp = _exp(salary_payment={"found": True, "page": 2, "phrase": "x", "status": ["Consistent", "Needs Attention"]})
    rep = _report(salary_payment=_finding("salary_payment", "Needs Attention", page=1))
    s = ev.score(exp, {"s": rep})
    assert s.found_correct == 10 and s.status_correct == 11 and s.unsafe_consistent == 0
    rep = _report(salary_payment=_finding("salary_payment", "Needs Attention", page=2))
    assert ev.score(exp, {"s": rep}).found_correct == 11


def test_score_missed_term_and_unsafe_consistent():
    exp = _exp(probation={"found": True, "page": 1, "phrase": "x", "status": "Needs Attention"})
    rep = _report(probation=_finding("probation", "Consistent", None, None),
                  notice_period=_finding("notice_period", "Consistent", None, None))
    s = ev.score(exp, {"s": rep})
    assert s.found_correct == 10
    assert s.status_correct == 9
    assert s.unsafe_consistent == 2


def _stub_analyse(status):
    def fn(pages, pipeline, llm, progress=None):
        return _report(salary_payment=_finding("salary_payment", status, page=1))
    return fn


def test_main_exit_codes(capsys):
    kw = dict(pipeline=object(), llm=object())
    assert ev.main(analyse_fn=_stub_analyse("Consistent"), **kw) == 1
    out = capsys.readouterr().out
    assert "salary_payment" in out and "unsafe" in out.lower()
    assert ev.main(analyse_fn=_stub_analyse("Unable to Assess"), **kw) == 0


def test_main_prints_no_contract_text(capsys):
    ev.main(analyse_fn=_stub_analyse("Consistent"), pipeline=object(), llm=object())
    assert "Harbourview" not in capsys.readouterr().out
