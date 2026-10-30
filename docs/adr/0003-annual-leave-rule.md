# 0003 – Annual leave: only ≥ 14 days is Consistent

Date: 2026-10-30 · Status: Accepted

## Context
Under s 88A of the Employment Act, the minimum annual leave is 7 days in the first year of service. It rises by 1 day per year, to 14 days from the 8th year. Most contracts state one flat number. A rule of "≥ 7 days → Consistent" would approve a flat 10 days, which is below the minimum from the 4th year onwards.

## Decision
- ≥ 14 days → `Consistent`.
- 7–13 days → `Needs Attention`. The reason says the amount meets the first-year minimum but the statutory minimum rises with service, and suggests asking the employer whether leave increases.
- < 7 days → `Needs Attention`, below the first-year minimum.
- Not found → `Unable to Assess`.
- The rule doesn't look at length of service or at whether the contract says leave increases (a richer option was considered and rejected for simplicity).

## Consequences
- The tool never wrongly approves a flat entitlement that later falls short.
- Contracts with a legitimate increasing schedule that starts below 14 days (e.g. "7 days, +1 per year") still get `Needs Attention`. The reason tells the user what to check, so this is acceptable.
