# 0014 – A separate model for each use case

Date: 2026-11-06 · Status: Accepted

## Context
One `LLM_MODEL` setting served both pages. The two use cases want different things from a model:
- **Contract Health Check** must never mark a term Consistent when it isn't (ADR 0011's pass mark).
- **Ask Your Contract** must answer questions its passages support, including "is X required?"
  questions where the honest answer is that the contract and sources are silent.

Real-model runs on 2026-11-06, with the code at that date:

| Model | Health Check: status correct | Health Check: unsafe Consistent | Q&A: on-topic answered | Q&A: off-topic refused |
|---|---|---|---|---|
| `gpt-4o-mini` | 53/55 | 0 | 13/15 | 3/3 |
| `gpt-4.1-mini` | 47–48/55 (2 runs) | 1 (both runs) | 15/15 | 3/3 |
| `gpt-5.4-mini` | 48–51/55 (2 runs) | 1–3 | 15/15 | 3/3 |
| `gpt-5.5` | 49/55 (2 runs) | 0 | 15/15 | 3/3 |

Health Check figures are `scripts/eval.py` (5 sample contracts × 11 terms). Q&A figures are 15
on-topic questions (two of them follow-ups) and 3 off-topic ones on `test_contract.pdf`. The
off-topic ones were refused by the threshold or by the model.

## Decision
- The health check keeps `LLM_MODEL`, default `gpt-4o-mini`: the only cheap model with 0 unsafe
  Consistent, and the best status accuracy.
- Q&A reads a new setting, `QA_LLM_MODEL`, default `gpt-5.4-mini`: it answered every on-topic
  question and refused every off-topic one. Its unsafe-Consistent results don't apply here,
  because Q&A has no statuses and its grounding is checked in code (ADR 0007).
- `LLM_MODEL` does not affect Q&A, so changing the health-check model can't silently change Q&A.

## Consequences
- Each page can be retuned or upgraded on its own. `gpt-5.5` is the fallback if one model must
  serve both pages: it passed both checks, at a higher cost and with more over-cautious statuses.
- Two settings to document and deploy instead of one.
- The samples are small, so the figures rule models out rather than rank close ones. Rerun the
  eval and the Q&A check before changing either default.
