# 0004 – Weekly hours: extract only when unambiguous, and show the figure

Date: 2026-10-30 · Status: Accepted

## Context
The 44-hour check (s 38) relies on `weekly_hours`, which the LLM supplies and the code can't verify. Contracts usually describe a daily schedule, not a weekly total. The model might count meal breaks, or flatten an alternating schedule into one number. s 38 allows up to 48 hours in one week if the other week is 40 or less.

## Decision
- The prompt tells the LLM to set `weekly_hours` only when the contract states a weekly total or it follows unambiguously from the schedule, excluding meal and rest breaks. For schedules that vary week to week, shifts or anything ambiguous, it leaves the field `null`.
- When the hours clause is found but `weekly_hours` is `null`, the result is `Unable to Assess` with a reason asking the user to check that hours average no more than 44 a week.
- Every hours reason states the figure used ("We read your contract as N hours a week, excluding breaks…").

## Consequences
- Misreadings can still happen, but the user can see them.
- Alternating schedules are never assessed, only flagged for the user to check.
- Shift workers (s 38 has separate rules for shift work) aren't covered by the rule, because of the null instruction.
