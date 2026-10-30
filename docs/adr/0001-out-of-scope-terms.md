# 0001 – Out-of-scope terms get a distinct reason, not a fourth status

Date: 2026-10-30 · Status: Accepted

## Context
Confidentiality and non-compete clauses are mainly governed by general contract law, not by the Employment Act or the MOM guidance pages in the knowledge base. Under the plan, those terms always end up `Unable to Assess` with an "insufficient evidence" reason. Users would read that as the tool failing, not as the sources being silent on the topic.

## Decision
- Keep exactly three statuses.
- `rules_engine.py` defines `OUT_OF_SCOPE_TERMS = {"confidentiality", "non_compete"}`. These always return `Unable to Assess` with `OUT_OF_SCOPE_REASON`, whether the clause is found or not. Rule-wins logic stops the LLM from overriding this.
- The extracted wording, the explanation and the employer question are still shown.
- The reason is limited to "the Employment Act and the MOM guidance used by this tool". It does not claim that no official guidance exists anywhere. Restrictive-covenant guidance could not be checked on 2026-10-30: guessed MOM and TAFEP URLs returned 404, and the indexed MOM pages don't mention it.

## Consequences
- `Unable to Assess` now has two different meanings for the user: "not enough information" and "outside these sources".
- If official restrictive-covenant guidance is found later, add it to `sources.json` and remove `non_compete` from the set.
