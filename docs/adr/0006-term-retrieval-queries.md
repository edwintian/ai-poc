# 0006 – Fixed per-term retrieval queries, enriched with contract wording

Date: 2026-10-30 · Status: Accepted

## Context
Because of the evidence guard (ADR 0005), a no-rule term only gets a useful finding if retrieval returns the right official passage. Searching on bare term keys ("probation", "deductions") is too short for embeddings, doesn't match the Act's wording ("deductions from salary", "termination of contract"), and ignores what the contract actually says.

## Decision
- `contract_analyser.TERM_QUERIES` holds one fixed query per term, phrased the way the official sources talk.
- When a term was found with verified wording (ADR 0002), the query becomes the base query followed by that wording.
- T4b step 6 checks retrieval with exactly these base queries. A query that misses is rephrased before the knowledge base is accepted.

## Consequences
- Retrieval is predictable and can be tuned in one place.
- Contract wording varies, so enriched queries can still drift. The T4b check covers only the base queries.
- The queries are part of the tool's behaviour: changing one can change findings, so re-run the T4b check after any change.
