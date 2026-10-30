# 0011 – Small real-model accuracy eval over the sample contracts

Date: 2026-10-30 · Status: Accepted

## Context
All automated tests use stub LLMs, so they check the code's logic but not real accuracy. Without a measurement, nobody can tell whether the extraction, recovery, query or threshold choices (ADRs 0002–0010) help or hurt, or whether a prompt change made things worse.

## Decision
- `sample_contracts/expected.json` holds the expected found/page/status for each of the 5 sample PDFs × 11 terms, plus a fixed employment context per sample. Where more than one status is defensible, a list of statuses is allowed.
- `scripts/eval.py` runs the real pipeline. It reports correct finds (page must match), status matches and unsafe `Consistent` results.
- Pass mark: zero unsafe `Consistent`. The other two numbers are reported, not gated.
- Automated tests only check that `expected.json` matches the generated PDFs and that the scoring logic is right. They never call the network.

## Consequences
- Prompt and query changes can be compared with numbers.
- Five synthetic contracts is a small, easy sample, so scores will look better than on real contracts. The README states this.
- Each run costs a few cents and needs the built KB.
