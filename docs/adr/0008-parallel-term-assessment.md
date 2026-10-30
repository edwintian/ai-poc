# 0008 – Assess terms in parallel, report progress from the script thread

Date: 2026-10-30 · Status: Accepted

## Context
One analysis makes 1 extraction call, then a retrieval and an assessment for each of the 11 terms. Run one after another, that's likely tens of seconds behind a spinner, and users may think the app has hung. The per-term calls are I/O-bound HTTP requests to OpenAI. The OpenAI client and a FAISS flat index can safely be used by several threads at once, and nothing modifies the contract index during `analyse`.

## Decision
- `analyse` runs the per-term retrieval and assessment in a `ThreadPoolExecutor(max_workers=4)`.
- Worker threads never call `st.*`. Streamlit UI calls only work from the script thread.
- `analyse` takes an optional `progress(done, total)` callback. It is called on the calling thread as each result arrives (`as_completed`). The Health Check page connects it to `st.progress`.
- Findings are put back into `TERM_KEYS` order. A failure on one term still only affects that term.
- The OpenAI SDK's default retries (2 attempts, with backoff for 429 and 5xx errors) stay on. No extra retry layer is added.

## Consequences
- Wall-clock time drops to roughly 3 rounds of calls instead of 11. Actual timing is recorded in the T9 manual check.
- If a Streamlit rerun interrupts an analysis, in-flight worker calls finish and their results are thrown away. That's harmless, apart from some API cost.
- Test stubs must be thread-safe, and assertions check results per term, not call order.
- Accounts on a low OpenAI rate-limit tier may see more retries. Lower `MAX_WORKERS` if they become a problem.
