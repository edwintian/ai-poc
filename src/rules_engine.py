from src.schemas import ContractTerms, ExtractedTerm, RuleResult, Source

MAX_WEEKLY_HOURS = 44  # s 38
MIN_OVERTIME_MULTIPLIER = 1.5  # s 38
ANNUAL_LEAVE_FIRST_YEAR = 7  # s 88A
ANNUAL_LEAVE_MAX = 14  # s 88A
WORKMAN_SALARY_CEILING = 4500  # s 35
NON_WORKMAN_SALARY_CEILING = 2600  # s 35

OUT_OF_SCOPE_TERMS = {"confidentiality", "non_compete"}
OUT_OF_SCOPE_REASON = (
    "The Employment Act and the MOM guidance used by this tool do not set rules for this term; "
    "it is mainly governed by general contract law, so consider professional advice if it concerns you."
)
HOURS_UNCLEAR_REASON = (
    "We couldn't work out a single weekly total from the contract wording (for example, the schedule "
    "varies from week to week). Check that your hours average no more than 44 a week, excluding breaks."
)
OVERTIME_NOT_FOUND_REASON = (
    "We couldn't find an overtime clause in the contract. If you're covered by Part 4 of the Employment "
    "Act, overtime must be paid at no less than 1.5 times your hourly basic rate, so check with your "
    "employer how overtime is handled. Part 4 covers workmen earning up to "
    f"${WORKMAN_SALARY_CEILING:,} a month and other employees (not managers or executives) earning up to "
    f"${NON_WORKMAN_SALARY_CEILING:,} a month in basic salary (s 35)."
)
_EMA = "https://sso.agc.gov.sg/Act/EmA1968"
RULE_SOURCES: dict[str, Source] = {
    "ema-s38": Source(title="Employment Act 1968", url=_EMA,
                      citation="Employment Act 1968 – 38. Hours of work"),
    "ema-s88a": Source(title="Employment Act 1968", url=_EMA,
                       citation="Employment Act 1968 – 88A. Annual leave"),
    "ema-s35": Source(title="Employment Act 1968", url=_EMA,
                      citation="Employment Act 1968 – 35. Application of this Part to certain workmen and other employees"),
}

# No user input on employee category or salary: hours and overtime are always checked, and every
# shortfall says the limits only apply where Part 4 covers the employee (ADR 0013).
PART4_NOTE = (
    "These limits are in Part 4 of the Employment Act, which covers workmen earning up to "
    f"${WORKMAN_SALARY_CEILING:,} a month and other employees (not managers or executives) earning up to "
    f"${NON_WORKMAN_SALARY_CEILING:,} a month in basic salary (s 35). If you're outside these groups, the limits "
    "may not apply to you. The Minister can change these figures, so check the current ones with MOM."
)
_SHORTFALL_IDS = ["ema-s38", "ema-s35"]


def _res(term: str, status: str, reason: str, ids: list[str]) -> RuleResult:
    return RuleResult(term=term, status=status, reason=reason, source_ids=ids)


def _num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


def _hours(t: ExtractedTerm) -> RuleResult:
    if not t.found:
        return _res("working_hours", "Unable to Assess",
                    "We couldn't find a working hours clause in the contract.", ["ema-s38"])
    if t.weekly_hours is None or t.weekly_hours <= 0:
        return _res("working_hours", "Unable to Assess", HOURS_UNCLEAR_REASON, ["ema-s38"])
    read = f"We read your contract as {_num(t.weekly_hours)} hours a week, excluding meal and rest breaks"
    if t.weekly_hours <= MAX_WEEKLY_HOURS:
        return _res("working_hours", "Consistent",
                    f"{read}, which is within the {MAX_WEEKLY_HOURS}-hour weekly limit.", ["ema-s38"])
    return _res("working_hours", "Needs Attention",
                f"{read}, which is above the {MAX_WEEKLY_HOURS}-hour weekly limit. {PART4_NOTE}", _SHORTFALL_IDS)


def _overtime(t: ExtractedTerm) -> RuleResult:
    if not t.found:
        return _res("overtime", "Needs Attention", OVERTIME_NOT_FOUND_REASON, _SHORTFALL_IDS)
    if t.overtime_multiplier is None or t.overtime_multiplier <= 0:
        return _res("overtime", "Unable to Assess",
                    "We couldn't determine the overtime rate from the contract wording.", ["ema-s38"])
    m = _num(t.overtime_multiplier)
    if t.overtime_multiplier >= MIN_OVERTIME_MULTIPLIER:
        return _res("overtime", "Consistent",
                    f"We read the overtime rate as {m} times your hourly basic rate, which meets the "
                    f"minimum of {MIN_OVERTIME_MULTIPLIER} times.", ["ema-s38"])
    return _res("overtime", "Needs Attention",
                f"We read the overtime rate as {m} times your hourly basic rate, which is below the "
                f"minimum of {MIN_OVERTIME_MULTIPLIER} times. {PART4_NOTE}", _SHORTFALL_IDS)


def _annual_leave(t: ExtractedTerm) -> RuleResult:
    ids = ["ema-s88a"]
    if not t.found:
        return _res("annual_leave", "Unable to Assess",
                    "We couldn't find an annual leave clause in the contract.", ids)
    d = t.annual_leave_days
    if d is None or d < 0:
        return _res("annual_leave", "Unable to Assess",
                    "We couldn't determine the number of annual leave days from the contract wording.", ids)
    if d >= ANNUAL_LEAVE_MAX:
        return _res("annual_leave", "Consistent",
                    f"{_num(d)} days meets the statutory annual leave entitlement for every year of service.", ids)
    if d >= ANNUAL_LEAVE_FIRST_YEAR:
        return _res("annual_leave", "Needs Attention",
                    f"Meets the first-year minimum of {ANNUAL_LEAVE_FIRST_YEAR} days, but the Act's minimum "
                    f"rises by one day per year of service to {ANNUAL_LEAVE_MAX} days from the 8th year. "
                    "Ask your employer whether leave increases with service.", ids)
    return _res("annual_leave", "Needs Attention",
                f"Below the first-year minimum of {ANNUAL_LEAVE_FIRST_YEAR} days.", ids)


_RULES = {"working_hours": _hours, "overtime": _overtime, "annual_leave": _annual_leave}


def rule_for(term: ExtractedTerm) -> RuleResult | None:
    if term.key in OUT_OF_SCOPE_TERMS:
        return _res(term.key, "Unable to Assess", OUT_OF_SCOPE_REASON, [])
    fn = _RULES.get(term.key)
    return fn(term) if fn else None


def run_rules(terms: ContractTerms) -> list[RuleResult]:
    results = (rule_for(t) for t in terms.terms)
    return [r for r in results if r is not None]
