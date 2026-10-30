# 0009 – Share only the read-only KB across sessions

Date: 2026-10-30 · Status: Accepted

## Context
`@st.cache_resource` returns one object shared by every user session. `RagPipeline` holds both the shared knowledge-base index and the uploaded contract index, and `index_contract` changes the pipeline in place. If the pipeline were cached, one user's contract would show up in another user's retrieval and Q&A, and the Clear button would affect both users. That's a privacy leak, and it never shows up when testing alone.

## Decision
- Cache only the read-only KB `VectorStore` (`load_kb()`).
- Each session builds its own `RagPipeline(load_kb(), embedder)` in `session_state["pipeline"]`.
- `index_contract` builds a separate contract store and never changes the KB store.
- Tests:
  - Two pipelines on the same KB stay independent.
  - The page's pipeline isn't the cached object, but it shares the cached KB.
  - A fresh `AppTest` session starts with no contract.

## Consequences
- One copy of the KB in memory (fits Streamlit Cloud's ~1 GB), with contract data isolated per session.
- Anyone adding new caching must keep contract-derived data out of `cache_resource` and `cache_data`.
