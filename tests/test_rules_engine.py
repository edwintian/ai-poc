import pytest

from src.rules_engine import (
    HOURS_UNCLEAR_REASON,
    OUT_OF_SCOPE_REASON,
    OVERTIME_NOT_FOUND_REASON,
    RULE_SOURCES,
    part4_applies,
    rule_for,
    run_rules,
)
from src.schemas import TERM_KEYS, ContractTerms, EmploymentContext, ExtractedTerm

STATUSES = {"Consistent", "Needs Attention", "Unable to Assess"}
COVERED = EmploymentContext(category="Workman", monthly_basic_salary=3000)


def T(key, found=True, **kw):
    base = dict(key=key, found=found, wording="w" if found else None, page=1 if found else None,
                weekly_hours=None, overtime_multiplier=None, annual_leave_days=None)
    base.update(kw)
    return ExtractedTerm(**base)


def test_rule_sources():
    assert set(RULE_SOURCES) == {"ema-s38", "ema-s88a", "ema-s35"}
    assert RULE_SOURCES["ema-s88a"].citation == "Employment Act 1968 – 88A. Annual leave"


@pytest.mark.parametrize("cat,sal,exp", [
    ("Workman", 4500, True), ("Workman", 4501, False), ("Non-workman", 2600, True),
    ("Non-workman", 2601, False), ("Manager or executive", 1000, False),
    ("Not sure", 1000, None), ("Workman", None, None), ("Non-workman", None, None),
])
def test_part4_applies(cat, sal, exp):
    assert part4_applies(EmploymentContext(category=cat, monthly_basic_salary=sal)) is exp


def test_hours_consistent_and_needs_attention():
    r = rule_for(T("working_hours", weekly_hours=44), COVERED)
    assert r.status == "Consistent" and "ema-s38" in r.source_ids
    assert "We read your contract as 44 hours a week, excluding meal and rest breaks" in r.reason
    r = rule_for(T("working_hours", weekly_hours=50), COVERED)
    assert r.status == "Needs Attention" and "ema-s38" in r.source_ids
    assert "We read your contract as 50 hours a week, excluding meal and rest breaks" in r.reason
    r = rule_for(T("working_hours", weekly_hours=45.5), COVERED)
    assert "45.5 hours a week" in r.reason


def test_hours_unclear_and_not_found():
    r = rule_for(T("working_hours", weekly_hours=None), COVERED)
    assert r.status == "Unable to Assess" and r.reason == HOURS_UNCLEAR_REASON
    assert rule_for(T("working_hours", found=False), COVERED).status == "Unable to Assess"


def test_hours_coverage_unknown_and_not_covered():
    r = rule_for(T("working_hours", weekly_hours=40), EmploymentContext())
    assert r.status == "Unable to Assess"
    assert "employee category" in r.reason and "monthly basic salary" in r.reason
    mgr = EmploymentContext(category="Manager or executive", monthly_basic_salary=9000)
    r = rule_for(T("working_hours", weekly_hours=60), mgr)
    assert r.status == "Unable to Assess" and "may not apply" in r.reason
    assert "Minister" in r.reason
    high = EmploymentContext(category="Workman", monthly_basic_salary=9000)
    assert "may not apply" in rule_for(T("overtime", overtime_multiplier=1.0), high).reason


def test_overtime():
    r = rule_for(T("overtime", overtime_multiplier=1.0), COVERED)
    assert r.status == "Needs Attention" and "ema-s38" in r.source_ids
    assert rule_for(T("overtime", overtime_multiplier=1.5), COVERED).status == "Consistent"
    assert rule_for(T("overtime", overtime_multiplier=2), COVERED).status == "Consistent"
    assert rule_for(T("overtime", overtime_multiplier=None), COVERED).status == "Unable to Assess"


def test_overtime_not_found():
    r = rule_for(T("overtime", found=False), COVERED)
    assert r.status == "Needs Attention" and r.reason == OVERTIME_NOT_FOUND_REASON
    assert "couldn't find" in r.reason and "does not provide" not in r.reason
    assert rule_for(T("overtime", found=False), EmploymentContext()).status == "Unable to Assess"
    mgr = EmploymentContext(category="Manager or executive", monthly_basic_salary=1)
    assert rule_for(T("overtime", found=False), mgr).status == "Unable to Assess"


def test_annual_leave():
    ctx = EmploymentContext()  # independent of Part 4 coverage
    for d in (14, 20):
        r = rule_for(T("annual_leave", annual_leave_days=d), ctx)
        assert r.status == "Consistent" and r.source_ids == ["ema-s88a"]
    r = rule_for(T("annual_leave", annual_leave_days=10), ctx)
    assert r.status == "Needs Attention" and "rises by one day per year of service" in r.reason
    r = rule_for(T("annual_leave", annual_leave_days=6), ctx)
    assert r.status == "Needs Attention" and "Below the first-year minimum of 7 days" in r.reason
    assert rule_for(T("annual_leave", found=False), ctx).status == "Unable to Assess"
    assert rule_for(T("annual_leave", annual_leave_days=None), ctx).status == "Unable to Assess"


@pytest.mark.parametrize("key", ["salary_payment", "sick_leave", "probation", "notice_period",
                                 "deductions", "termination"])
def test_no_rule(key):
    assert rule_for(T(key), COVERED) is None


@pytest.mark.parametrize("key", ["confidentiality", "non_compete"])
@pytest.mark.parametrize("found", [True, False])
def test_out_of_scope(key, found):
    r = rule_for(T(key, found=found), COVERED)
    assert r.status == "Unable to Assess" and r.reason == OUT_OF_SCOPE_REASON
    assert r.source_ids == []


def test_run_rules_all_not_found_never_consistent_and_no_legal_wording():
    terms = ContractTerms(is_employment_contract=True,
                          terms=[T(k, found=False) for k in TERM_KEYS])
    for ctx in (COVERED, EmploymentContext()):
        res = run_rules(terms, ctx)
        assert {r.term for r in res} == {"working_hours", "overtime", "annual_leave",
                                         "confidentiality", "non_compete"}
        assert all(r.status in STATUSES and r.status != "Consistent" for r in res)


def test_no_legal_wording_anywhere():
    cases = [T("working_hours", weekly_hours=h) for h in (None, 40, 50)] + [
        T("working_hours", found=False), T("overtime", overtime_multiplier=1.0),
        T("overtime", overtime_multiplier=2), T("overtime", overtime_multiplier=None),
        T("overtime", found=False)] + [T("annual_leave", annual_leave_days=d) for d in (None, 3, 10, 14)
    ] + [T("annual_leave", found=False), T("confidentiality"), T("non_compete", found=False)]
    ctxs = [COVERED, EmploymentContext(), EmploymentContext(category="Manager or executive",
                                                           monthly_basic_salary=9000)]
    for c in ctxs:
        for t in cases:
            r = rule_for(t, c)
            assert "legal" not in r.reason.lower()
    assert "legal" not in OVERTIME_NOT_FOUND_REASON.lower()


@pytest.mark.parametrize("h", [0, -5])
def test_non_positive_hours_unable(h):
    r = rule_for(T("working_hours", weekly_hours=h), COVERED)
    assert r.status == "Unable to Assess" and r.reason == HOURS_UNCLEAR_REASON


@pytest.mark.parametrize("m", [0, -1.5])
def test_non_positive_overtime_unable(m):
    r = rule_for(T("overtime", overtime_multiplier=m), COVERED)
    assert r.status == "Unable to Assess" and "couldn't determine the overtime rate" in r.reason


def test_negative_leave_unable():
    r = rule_for(T("annual_leave", annual_leave_days=-3), COVERED)
    assert r.status == "Unable to Assess" and "couldn't determine" in r.reason


@pytest.mark.parametrize("cat", ["Workman", "Non-workman"])
@pytest.mark.parametrize("sal", [0, -100])
def test_non_positive_salary_unknown(cat, sal):
    assert part4_applies(EmploymentContext(category=cat, monthly_basic_salary=sal)) is None


def test_leave_boundaries():
    r = rule_for(T("annual_leave", annual_leave_days=7), COVERED)
    assert r.status == "Needs Attention" and "rises by one day per year of service" in r.reason
    assert rule_for(T("annual_leave", annual_leave_days=13), COVERED).status == "Needs Attention"


def test_manager_without_salary_is_not_covered():
    assert part4_applies(EmploymentContext(category="Manager or executive")) is False


def test_unknown_coverage_reason_wording():
    r = rule_for(T("working_hours", weekly_hours=40), EmploymentContext())
    assert "We need your employee category and monthly basic salary" in r.reason
    assert "Minister" in r.reason
