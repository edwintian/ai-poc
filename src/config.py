import os

import streamlit as st
from dotenv import load_dotenv

_dotenv_loaded = False


def get_secret(name: str) -> str | None:
    """Env var (incl. .env) first, then st.secrets; blank values count as missing."""
    global _dotenv_loaded
    if not _dotenv_loaded:
        load_dotenv(override=False)
        _dotenv_loaded = True
    value = (os.environ.get(name) or "").strip()
    if value:
        return value
    try:
        value = str(st.secrets[name]).strip()
    except Exception:  # no secrets file, or key absent
        return None
    return value or None
