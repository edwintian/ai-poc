from src.schemas import ContractTerms, EmploymentContext, ExtractedTerm, RuleResult, Source

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
    "employer how overtime is handled."
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

_CEILING_NOTE = "The salary ceilings can be changed by the Minister, so check the current figures with MOM."
NO_PART4_REASON = (
    "Part 4 of the Employment Act (hours and overtime) may not apply to you, because of your employee "
    "category or monthly basic salary, so we can't assess this term against it. " + _CEILING_NOTE
)
UNKNOWN_COVERAGE_REASON = (
    "Whether Part 4 of the Employment Act (hours and overtime) applies depends on your employee category "
    "and monthly basic salary. We need your employee category and monthly basic salary to tell whether these rules apply to you. "
    + _CEILING_NOTE
)


def part4_applies(ctx: EmploymentContext) -> bool | None:
    """s 35: Part 4 coverage by category and salary ceiling."""
    if ctx.category == "Manager or executive":
        return False
    sal = ctx.monthly_basic_salary
    if sal is None or sal <= 0:
        return None
    if ctx.category == "Workman":
        return sal <= WORKMAN_SALARY_CEILING
    if ctx.category == "Non-workman":
        return sal <= NON_WORKMAN_SALARY_CEILING
    return None


def _res(term: str, status: str, reason: str, ids: list[str]) -> RuleResult:
    return RuleResult(term=term, status=status, reason=reason, source_ids=ids)


def _num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


def _coverage_gate(key: str, applies: bool | None) -> RuleResult | None:
    if applies is False:
        return _res(key, "Unable to Assess", NO_PART4_REASON, ["ema-s38", "ema-s35"])
    if applies is None:
        return _res(key, "Unable to Assess", UNKNOWN_COVERAGE_REASON, ["ema-s38", "ema-s35"])
    return None


def _hours(t: ExtractedTerm, ctx: EmploymentContext) -> RuleResult:
    gate = _coverage_gate("working_hours", part4_applies(ctx))
    if gate:
        return gate
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
                f"{read}, which is above the {MAX_WEEKLY_HOURS}-hour weekly limit.", ["ema-s38"])


def _overtime(t: ExtractedTerm, ctx: EmploymentContext) -> RuleResult:
    applies = part4_applies(ctx)
    if not t.found:
        if applies is True:
            return _res("overtime", "Needs Attention", OVERTIME_NOT_FOUND_REASON, ["ema-s38"])
        return _coverage_gate("overtime", applies)
    gate = _coverage_gate("overtime", applies)
    if gate:
        return gate
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
                f"minimum of {MIN_OVERTIME_MULTIPLIER} times.", ["ema-s38"])


def _annual_leave(t: ExtractedTerm, ctx: EmploymentContext) -> RuleResult:
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


def rule_for(term: ExtractedTerm, ctx: EmploymentContext) -> RuleResult | None:
    if term.key in OUT_OF_SCOPE_TERMS:
        return _res(term.key, "Unable to Assess", OUT_OF_SCOPE_REASON, [])
    fn = _RULES.get(term.key)
    return fn(term, ctx) if fn else None


def run_rules(terms: ContractTerms, ctx: EmploymentContext) -> list[RuleResult]:
    results = (rule_for(t, ctx) for t in terms.terms)
    return [r for r in results if r is not None]
