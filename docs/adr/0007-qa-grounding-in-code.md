# 0007 – Q&A grounding is enforced in code

Date: 2026-10-30 · Status: Accepted

## Context
Originally, Q&A refused only when retrieval found nothing above `min_score=0.25`. That threshold was never tested with real `text-embedding-3-small` scores. An off-topic question could pull in a weakly related passage, and then the only limits on the answer were prompt instructions the code never checked. This is the same gap ADR 0005 closed for findings.

## Decision
- `answer` uses `complete_structured(..., QAResponse)` with the fields `answerable`, `answer` and `cited_ids`.
- Code shows `REFUSAL` in two cases: when `answerable` is false, or when no cited id matches a retrieved passage. Contract passages count as valid citations for Q&A.
- The returned turn only carries the cited passages (`filter_evidence`), so the UI shows what the answer relied on.
- A T8 manual step checks with real embeddings that 0.25 separates on-topic from off-topic questions. If it doesn't, the threshold is re-set.

## Consequences
- Every answer shown to the user cites at least one real retrieved passage.
- Code can't check that the answer text actually matches what it cites. That still relies on the prompt.
- Some answerable questions will be refused when the LLM forgets to cite. We accept refusing over an ungrounded answer.
