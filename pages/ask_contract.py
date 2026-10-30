import streamlit as st

from src import llm as llm_mod
from src import qa
from src import rag_pipeline as rp
from src.contract_analyser import DISCLAIMER
from src.schemas import ChatTurn
from src.ui import md_escape

EXCERPT_CHARS = 300


def render_turn(turn: ChatTurn) -> None:
    with st.chat_message(turn.role):
        st.markdown(md_escape(turn.content))
        ev = turn.evidence
        if ev is None or not (ev.contract or ev.official):
            return
        with st.expander("Sources"):
            for h in ev.contract:
                p = h.passage
                where = f"Contract, p. {p.page}" if p.page is not None else "Contract"
                st.markdown(f"**{where}:** {md_escape(p.text[:EXCERPT_CHARS])}")
            links = []
            for h in ev.official:
                s = rp.to_source(h.passage)
                if s is not None:
                    links.append(f"- [{md_escape(s.citation)}]({s.url})")
            if links:
                st.markdown("**Official sources:**\n" + "\n".join(links))


st.session_state.setdefault("chat", [])

st.title("Ask Your Contract")
pipeline = st.session_state.get("pipeline")

if pipeline is None or pipeline.contract is None:
    st.info("Analyse a contract first on the Contract Health Check page, then ask questions here.")
    try:
        st.page_link("pages/health_check.py", label="Go to Contract Health Check")
    except Exception:
        pass
else:
    st.caption(DISCLAIMER)
    for turn in st.session_state["chat"]:
        render_turn(turn)
    question = st.chat_input("Ask a question about your contract")
    if question:
        try:
            reply = qa.answer(question, st.session_state["chat"], pipeline, llm_mod.OpenAIClient())
        except (llm_mod.LLMError, rp.RetrievalError):
            st.error("The question service is unavailable right now; please try again.")
        else:
            st.session_state["chat"] = st.session_state["chat"] + [
                ChatTurn(role="user", content=question), reply]
            st.rerun()
