# 0010 – Second-chance recovery for terms missed by extraction

Date: 2026-10-30 · Status: Accepted

## Context
Extraction asks one LLM call for all 11 terms across a contract of up to 40 pages. A small model misses clauses buried deep in the document, and ADR 0002 turns misquotes into misses too. Every miss shows as "Not found in contract". That quietly lowers accuracy and usually leads to `Unable to Assess`.

## Decision
- Keep the single extraction call.
- For each term still not found, if retrieval returned contract hits for that term's query (ADR 0006), make one focused `complete_structured(..., ExtractedTerm)` call over only those hits. Run it inside the parallel per-term worker (ADR 0008).
- The recovered quote goes through the same `verify_term` check, so unverified quotes still mean not found.
- Rules now run per term (`rule_for`) after recovery, so recovered values are judged.
- A recovery failure leaves the term not found and doesn't create a service-error finding.
- Official evidence from the base-query retrieval is reused.

## Consequences
- Fewer false "Not found" results, at the cost of roughly one extra small LLM call per missed term.
- Recovery only sees the top contract hits (`k_contract=3`). A clause that retrieval can't surface stays missed.
- The recovery prompt carries the same untrusted-data guard as extraction.
