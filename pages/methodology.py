import streamlit as st

HEALTH_CHECK_DOT = """
digraph G {
  rankdir=TB;
  node [shape=box, style=rounded, fontsize=11];
  upload [label="Upload PDF"];
  parse [label="Parse pages"];
  extract [label="Extract terms"];
  verify1 [label="Verify quotes"];
  upload -> parse -> extract -> verify1;
  subgraph cluster_term {
    label="Per term (parallel)"; style=dashed; fontsize=11;
    retrieve [label="Retrieve official +\\ncontract passages"];
    missing [label="Not found?", shape=diamond];
    recover [label="Recover"];
    verify2 [label="Verify quotes"];
    rules [label="Rules engine"];
    assess [label="Assess term"];
    guard [label="Evidence check"];
    retrieve -> missing;
    missing -> recover [label="yes"];
    recover -> verify2 -> rules;
    missing -> rules [label="no"];
    rules -> assess -> guard;
  }
  report [label="Findings report"];
  verify1 -> retrieve;
  guard -> report;
}
"""

QA_DOT = """
digraph G {
  rankdir=TB;
  node [shape=box, style=rounded, fontsize=11];
  q [label="Question"];
  retrieve [label="Retrieve (same pipeline)"];
  found [label="Evidence found?", shape=diamond];
  refuse1 [label="Refuse"];
  llm [label="LLM answer"];
  ok [label="Answerable and cites a retrieved passage?", shape=diamond];
  refuse2 [label="Refuse"];
  answer [label="Grounded answer\\nwith citations"];
  q -> retrieve -> found;
  found -> refuse1 [label="no"];
  found -> llm [label="yes"];
  llm -> ok;
  ok -> refuse2 [label="no"];
  ok -> answer [label="yes"];
}
"""

ADRS = [
    ("0001", "Out-of-scope terms get a distinct reason, not a fourth status"),
    ("0002", "Unverified quotes count as \"not found\""),
    ("0003", "Annual leave: only ≥ 14 days is Consistent"),
    ("0004", "Weekly hours: extract only when unambiguous, and show the figure"),
    ("0005", "Evidence guard applies to Needs Attention as well as Consistent"),
    ("0006", "Fixed per-term retrieval queries, enriched with contract wording"),
    ("0007", "Q&A grounding is enforced in code"),
    ("0008", "Assess terms in parallel, report progress from the script thread"),
    ("0009", "Share only the read-only KB across sessions"),
    ("0010", "Second-chance recovery for terms missed by extraction"),
    ("0011", "Small real-model accuracy eval over the sample contracts"),
    ("0012", "Secrets stay with the user; deployment uses the user's own accounts"),
]

st.title("Methodology")

st.header("Data flows")
st.markdown(
    """
**Contract Health Check.** The PDF is parsed page by page. The model extracts
the 11 terms with a verbatim quote for each, and every quote is checked against
the contract text. For each term, the app retrieves official passages (the Act
and MOM guidance) and passages from the contract. A term the extraction missed
gets a second chance. The rules engine then applies fixed checks where the
law gives a clear number, and the model assesses the rest. A final evidence
check turns any finding without official support into Unable to Assess.

**Ask Your Contract.** The question goes through the same retrieval. With no
evidence above the threshold, the app refuses without calling the model.
Otherwise the model answers, and the answer is kept only if the model says it
is answerable and cites a passage that was actually retrieved.
"""
)

st.header("Implementation details")
st.markdown(
    """
- **Parser:** extracts text per page from the PDF and rejects invalid or
  empty files with a clear message.
- **Chunking:** sources are split by heading and long sections are packed into passages of limited length, giving
  305 passages. The contract is chunked per session, keeping page numbers.
- **Embeddings:** OpenAI `text-embedding-3-small`.
- **Vector store:** FAISS inner product on normalised vectors (cosine
  similarity). The knowledge base index is read-only and shared; each
  session has its own contract index.
- **Retrieval:** a fixed query per term, enriched with the contract's own
  wording. Minimum scores are 0.25 for the health check and, for Q&A, 0.27 for
  contract passages and 0.40 for official ones. These came from a check on
  2026-10-30 where 7 of 7 on-topic questions were answered and 7 of 7
  off-topic ones were refused.
- **Rules engine:** weekly hours of 44 or fewer and overtime of at least 1.5
  times pay (s 38), only when Part 4 applies (s 35: workmen earning up to
  $4,500 a month, other non-managerial employees up to $2,600 a month, or
  such other amount as the Minister may prescribe). Annual leave follows
  s 88A (7 days in year 1 rising to 14), and only 14 or more is Consistent.
  Confidentiality and non-compete are out of scope.
- **LLM:** `gpt-4o-mini` by default (the `LLM_MODEL` setting overrides it),
  using structured outputs, so malformed replies are rejected, not guessed at.
  The statuses are defined in the assessment prompt.
- **Guards:** quote verification, the two-way evidence guard, and
  grounding checks in code for Q&A. Untrusted text is escaped in the UI.
- **Parallelism:** terms are assessed with 4 workers. Progress is reported
  from the main script thread.
- **Session state:** the contract, index and results live in the session only.
  Clearing the session removes them.
"""
)

st.header("Evaluation")
st.markdown(
    """
The assessment was checked on 5 synthetic contracts across 11 terms (55
cases) with `gpt-4o-mini` on 2026-10-30.

- First run: 6 unsafe Consistent results. This led to defining the three
  statuses in the assessment prompt.
- Second run: all 55 terms found, status correct for 52 of 55, and 0 unsafe
  Consistent. The 3 mismatches were over-cautious Needs Attention.

This is a small synthetic sample, so treat it as a sanity check and not as a
measure of real-world accuracy.
"""
)

st.header("Flowcharts")
st.subheader("Use Case 1: Contract Health Check")
st.graphviz_chart(HEALTH_CHECK_DOT)
st.subheader("Use Case 2: Ask Your Contract")
st.graphviz_chart(QA_DOT)

st.subheader("Safeguards")
st.markdown("Design decisions are recorded as architecture decision records (ADRs).")
st.markdown("\n".join(f"- **ADR {n}:** {t}" for n, t in ADRS))
