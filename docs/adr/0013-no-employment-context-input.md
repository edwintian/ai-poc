# 0013 – No employee category or salary input; always check hours and overtime

Date: 2026-11-06 · Status: Accepted (supersedes the Part 4 coverage gate in the rules engine)

## Context
The health check asked for an "Employment category" (Workman / Non-workman / Manager or executive / Not sure) and an optional monthly basic salary, to decide whether Part 4 of the Employment Act (hours, overtime) applies under s 35. Only "workman" is defined in the Act (s 2); "non-workman" is not the Act's term, and "managerial or executive position" is undefined there. Users could not reliably place themselves, job titles mislead (e.g. "Assistant Manager"), and the default "Not sure" turned hours and overtime into `Unable to Assess` for most users.

## Decision
- Remove both inputs and `EmploymentContext`; `analyse`, `rule_for` and `run_rules` no longer take a context.
- Always check working hours (≤ 44/week) and overtime (≥ 1.5×) under s 38.
- A shortfall (hours over 44, overtime below 1.5×, or no overtime clause found) is `Needs Attention`, and its reason states the s 35 coverage groups and ceilings and that the limits may not apply outside them. It cites s 38 and s 35.
- A `Consistent` result carries no caveat: meeting the Part 4 standard is fine whether or not Part 4 applies.

## Consequences
- No unsafe `Consistent` is introduced; the change can only add `Needs Attention` for employees outside Part 4, with a reason that explains why it may not apply.
- Managers, executives and higher earners may see hours/overtime flags that don't apply to them; the reason tells them so.
- `expected.json` loses `_context`; `varied_notice_leave` (S$5,800, outside Part 4) now expects hours `Consistent`/`Unable to Assess` and overtime `Needs Attention`.
