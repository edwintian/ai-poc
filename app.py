import streamlit as st

from src.auth import check_password
from src.config import get_secret

st.set_page_config(page_title="Singapore Employment Contract Checker")

if not st.session_state.get("authed"):
    expected = get_secret("APP_PASSWORD") or ""
    if not expected:
        st.error("The app password is not configured. Set APP_PASSWORD to enable login.")
        st.stop()
    with st.form("login"):
        supplied = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")
    if submitted and check_password(supplied, expected):
        st.session_state["authed"] = True
        st.rerun()
    if submitted:
        st.error("Incorrect password.")
    st.stop()

st.navigation([
    st.Page("pages/health_check.py", title="Contract Health Check"),
    st.Page("pages/ask_contract.py", title="Ask Your Contract"),
    st.Page("pages/about.py", title="About Us"),
    st.Page("pages/methodology.py", title="Methodology"),
]).run()
