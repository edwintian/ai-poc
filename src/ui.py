"""Small UI helpers shared by the Streamlit pages."""

_MD_SPECIALS = set("\\`*_{}[]()#+-.!|<>$~")


def md_escape(text: str) -> str:
    """Backslash-escape markdown specials so untrusted text renders literally."""
    return "".join("\\" + c if c in _MD_SPECIALS else c for c in text)
