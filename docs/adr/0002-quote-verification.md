# 0002 – Unverified quotes count as "not found"

Date: 2026-10-30 · Status: Accepted

## Context
The LLM extracts the wording of each term. A made-up or misquoted clause would mislead the user. On the other hand, strict matching can reject real clauses because of page breaks, quotes the LLM shortened, or PDF text quirks.

## Decision
- Code verifies each quote against the contract text after normalisation: ligatures expanded, quote marks and dashes straightened, hyphens removed (including line-break hyphens), whitespace collapsed, case-folded. Matching runs over all pages joined together, so a quote can cross a page break. The page shown is the one where the match starts.
- The prompt asks for verbatim quotes with no ellipses.
- A quote that still doesn't match marks the term `found=False`, and its wording, page and numeric values are cleared. There is no "found but unverified" state.

## Consequences
- The tool never shows unverified contract wording or page numbers, and never runs rules on numbers taken from a rejected quote.
- Not-found means "we couldn't find it", not "it's absent". Any reason given for a not-found term must stay true if the clause actually exists. Example: overtime not found while Part 4 applies is still `Needs Attention`, with the reason "We couldn't find an overtime clause…", never "the contract does not provide overtime" (decided 2026-10-30).
- Some real clauses will show as "Not found in contract", which usually leads to `Unable to Assess`. We accept this false negative over the risk of fabricated evidence.
