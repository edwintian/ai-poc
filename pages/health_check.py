import pandas as pd
import streamlit as st

from src import contract_analyser as ca
from src import document_parser as dp
from src import llm as llm_mod
from src import rag_pipeline as rp
from src.schemas import EmploymentContext, TERM_KEYS

KB_DIR = "data/knowledge_base"
NOT_FOUND = "Not found in contract"
TERM_LABELS = {
    "salary_payment": "Salary payment",
    "working_hours": "Working hours",
    "overtime": "Overtime",
    "annual_leave": "Annual leave",
    "sick_leave": "Sick leave",
    "probation": "Probation",
    "notice_period": "Notice period",
    "deductions": "Deductions",
    "termination": "Termination",
    "confidentiality": "Confidentiality",
    "non_compete": "Non-compete",
}
CATEGORIES = ["Not sure", "Workman", "Non-workman", "Manager or executive"]


@st.cache_resource
def load_kb():
    # Read-only knowledge base only; never cache anything holding contract data (ADR 0009).
    return rp.VectorStore.load(KB_DIR)


def _label(key: str) -> str:
    return TERM_LABELS.get(key, key)


st.session_state.setdefault("report", None)
st.session_state.setdefault("chat", [])
st.session_state.setdefault("context", None)

st.title("Contract Health Check")
st.write("Upload an employment contract to see how its key terms compare with Singapore law and MOM guidance.")
st.info("The contract text is sent to OpenAI for analysis and is not stored after your session ends.")

uploaded = st.file_uploader("Employment contract (PDF)", type=["pdf"])
category = st.selectbox("Employment category", CATEGORIES, index=0)
salary = st.number_input(
    "Monthly basic salary (optional, S$)", min_value=0.0, value=None, step=100.0,
    help="Part 4 of the Employment Act covers workmen earning up to $4,500 and others up to "
         "$2,600 a month. The Minister can change these ceilings.",
)

if st.button("Analyze", key="analyze", type="primary", disabled=uploaded is None):
    st.session_state["report"] = None
    ctx = EmploymentContext(category=category, monthly_basic_salary=salary)
    try:
        data = uploaded.getvalue()  # read here only; never kept in session state
        pages = dp.parse_pdf(data)
        del data
        if st.session_state.get("pipeline") is None:
            try:
                kb = load_kb()
            except (FileNotFoundError, ValueError):
                st.error("The knowledge base is missing or unreadable. Build it with "
                         "`python scripts/build_kb.py` and restart the app.")
                st.stop()
            st.session_state["pipeline"] = rp.RagPipeline(kb, rp.OpenAIEmbedder())
        bar = st.progress(0, text="Starting analysis")

        def progress(done: int, total: int) -> None:
            bar.progress(done / total, text=f"Assessing term {done} of {total}")

        report = ca.analyse(pages, ctx, st.session_state["pipeline"], llm_mod.OpenAIClient(),
                            progress=progress)
        st.session_state["report"] = report
        st.session_state["context"] = ctx
        bar.empty()
    except dp.UnreadableDocument as e:
        st.error(str(e))
    except ca.NotAContract:
        st.error("This doesn't look like an employment contract. Please upload a PDF of your "
                 "employment contract.")
    except (llm_mod.LLMError, rp.RetrievalError):
        st.error("The analysis service is unavailable right now; please try again.")

report = st.session_state["report"]
if report is not None:
    st.subheader("Results")
    st.dataframe(
        pd.DataFrame({
            "Term": [_label(f.term) for f in report.findings],
            "Status": [f.status for f in report.findings],
            "Wording": [f.wording or NOT_FOUND for f in report.findings],
        }),
        hide_index=True,
    )
    for f in report.findings:
        with st.expander(f"{_label(f.term)}: {f.status}"):
            st.markdown(f"**Status:** {f.status}")
            if f.wording is None:
                st.markdown(f"**Contract wording:** {NOT_FOUND}")
            else:
                page = f" (page {f.page})" if f.page is not None else ""
                st.markdown(f"**Contract wording:** {f.wording}{page}")
            st.markdown(f"**Explanation:** {f.explanation}")
            st.markdown(f"**Reason:** {f.reason}")
            if f.sources:
                st.markdown("**Sources:**\n" + "\n".join(f"- [{s.citation}]({s.url})" for s in f.sources))
            if f.question:
                st.markdown(f"**Question to ask:** {f.question}")
    st.caption(report.disclaimer)
    if st.button("Clear contract & results", key="clear"):
        st.session_state["report"] = None
        pipeline = st.session_state.get("pipeline")
        if pipeline is not None:
            pipeline.clear_contract()
        st.session_state["chat"] = []
        st.rerun()
