# 0005 – Evidence guard applies to Needs Attention as well as Consistent

Date: 2026-10-30 · Status: Accepted

## Context
Six terms have no rule: salary_payment, sick_leave, probation, notice_period, deductions and termination. For these, the LLM's status stands. The original guard only downgraded `Consistent` when there was no evidence. So the LLM could flag a term `Needs Attention` from its own general knowledge with no source behind it, which makes the LLM the legal source of truth.

## Decision
When there is no rule, both `Consistent` and `Needs Attention` need at least one cited id that resolves to a retrieved official passage. Otherwise the finding becomes `Unable to Assess` with `INSUFFICIENT_EVIDENCE_REASON`. Rule and out-of-scope results are never changed by this guard.

## Consequences
- Every finding the user sees on a no-rule term has a source behind it.
- Some real problems become `Unable to Assess` when retrieval misses the right passage. We prefer that to an unsourced alarm (an alternative was considered and rejected).
- Retrieval quality for those six terms now directly affects how many findings are useful. Worth checking in the T4b top-3 retrieval check.
