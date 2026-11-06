import pytest

from src.rules_engine import (
    HOURS_UNCLEAR_REASON,
    OUT_OF_SCOPE_REASON,
    OVERTIME_NOT_FOUND_REASON,
    PART4_NOTE,
    RULE_SOURCES,
    rule_for,
    run_rules,
)
from src.schemas import TERM_KEYS, ContractTerms, ExtractedTerm

STATUSES = {"Consistent", "Needs Attention", "Unable to Assess"}


def T(key, found=True, **kw):
    base = dict(key=key, found=found, wording="w" if found else None, page=1 if found else None,
                weekly_hours=None, overtime_multiplier=None, annual_leave_days=None)
    base.update(kw)
    return ExtractedTerm(**base)


def test_rule_sources():
    assert set(RULE_SOURCES) == {"ema-s38", "ema-s88a", "ema-s35"}
    assert RULE_SOURCES["ema-s88a"].citation == "Employment Act 1968 – 88A. Annual leave"


def test_hours_consistent_and_needs_attention():
    r = rule_for(T("working_hours", weekly_hours=44))
    assert r.status == "Consistent" and "ema-s38" in r.source_ids
    assert "We read your contract as 44 hours a week, excluding meal and rest breaks" in r.reason
    r = rule_for(T("working_hours", weekly_hours=50))
    assert r.status == "Needs Attention" and "ema-s38" in r.source_ids
    assert "We read your contract as 50 hours a week, excluding meal and rest breaks" in r.reason
    r = rule_for(T("working_hours", weekly_hours=45.5))
    assert "45.5 hours a week" in r.reason


def test_hours_unclear_and_not_found():
    r = rule_for(T("working_hours", weekly_hours=None))
    assert r.status == "Unable to Assess" and r.reason == HOURS_UNCLEAR_REASON
    assert rule_for(T("working_hours", found=False)).status == "Unable to Assess"


def test_shortfalls_carry_part4_caveat_and_s35():
    for t in (T("working_hours", weekly_hours=50), T("overtime", overtime_multiplier=1.25)):
        r = rule_for(t)
        assert r.status == "Needs Attention" and PART4_NOTE in r.reason
        assert r.source_ids == ["ema-s38", "ema-s35"]
    assert "Minister" in PART4_NOTE and "$4,500" in PART4_NOTE and "$2,600" in PART4_NOTE
    assert "managers or executives" in PART4_NOTE


def test_consistent_hours_and_overtime_have_no_caveat():
    for t in (T("working_hours", weekly_hours=40), T("overtime", overtime_multiplier=1.5)):
        r = rule_for(t)
        assert r.status == "Consistent" and PART4_NOTE not in r.reason and r.source_ids == ["ema-s38"]


def test_overtime():
    r = rule_for(T("overtime", overtime_multiplier=1.0))
    assert r.status == "Needs Attention" and "ema-s38" in r.source_ids
    assert rule_for(T("overtime", overtime_multiplier=1.5)).status == "Consistent"
    assert rule_for(T("overtime", overtime_multiplier=2)).status == "Consistent"
    assert rule_for(T("overtime", overtime_multiplier=None)).status == "Unable to Assess"


def test_overtime_not_found():
    r = rule_for(T("overtime", found=False))
    assert r.status == "Needs Attention" and r.reason == OVERTIME_NOT_FOUND_REASON
    assert "couldn't find" in r.reason and "does not provide" not in r.reason
    assert "$4,500" in r.reason and "$2,600" in r.reason


def test_annual_leave():
    for d in (14, 20):
        r = rule_for(T("annual_leave", annual_leave_days=d))
        assert r.status == "Consistent" and r.source_ids == ["ema-s88a"]
    r = rule_for(T("annual_leave", annual_leave_days=10))
    assert r.status == "Needs Attention" and "rises by one day per year of service" in r.reason
    r = rule_for(T("annual_leave", annual_leave_days=6))
    assert r.status == "Needs Attention" and "Below the first-year minimum of 7 days" in r.reason
    assert rule_for(T("annual_leave", found=False)).status == "Unable to Assess"
    assert rule_for(T("annual_leave", annual_leave_days=None)).status == "Unable to Assess"


@pytest.mark.parametrize("key", ["salary_payment", "sick_leave", "probation", "notice_period",
                                 "deductions", "termination"])
def test_no_rule(key):
    assert rule_for(T(key)) is None


@pytest.mark.parametrize("key", ["confidentiality", "non_compete"])
@pytest.mark.parametrize("found", [True, False])
def test_out_of_scope(key, found):
    r = rule_for(T(key, found=found))
    assert r.status == "Unable to Assess" and r.reason == OUT_OF_SCOPE_REASON
    assert r.source_ids == []


def test_run_rules_all_not_found_never_consistent_and_no_legal_wording():
    terms = ContractTerms(is_employment_contract=True,
                          terms=[T(k, found=False) for k in TERM_KEYS])
    res = run_rules(terms)
    assert {r.term for r in res} == {"working_hours", "overtime", "annual_leave",
                                     "confidentiality", "non_compete"}
    assert all(r.status in STATUSES and r.status != "Consistent" for r in res)


def test_no_legal_wording_anywhere():
    cases = [T("working_hours", weekly_hours=h) for h in (None, 40, 50)] + [
        T("working_hours", found=False), T("overtime", overtime_multiplier=1.0),
        T("overtime", overtime_multiplier=2), T("overtime", overtime_multiplier=None),
        T("overtime", found=False)] + [T("annual_leave", annual_leave_days=d) for d in (None, 3, 10, 14)
    ] + [T("annual_leave", found=False), T("confidentiality"), T("non_compete", found=False)]
    for t in cases:
        assert "legal" not in rule_for(t).reason.lower()
    assert "legal" not in OVERTIME_NOT_FOUND_REASON.lower()


@pytest.mark.parametrize("h", [0, -5])
def test_non_positive_hours_unable(h):
    r = rule_for(T("working_hours", weekly_hours=h))
    assert r.status == "Unable to Assess" and r.reason == HOURS_UNCLEAR_REASON


@pytest.mark.parametrize("m", [0, -1.5])
def test_non_positive_overtime_unable(m):
    r = rule_for(T("overtime", overtime_multiplier=m))
    assert r.status == "Unable to Assess" and "couldn't determine the overtime rate" in r.reason


def test_negative_leave_unable():
    r = rule_for(T("annual_leave", annual_leave_days=-3))
    assert r.status == "Unable to Assess" and "couldn't determine" in r.reason


def test_leave_boundaries():
    r = rule_for(T("annual_leave", annual_leave_days=7))
    assert r.status == "Needs Attention" and "rises by one day per year of service" in r.reason
    assert rule_for(T("annual_leave", annual_leave_days=13)).status == "Needs Attention"
