"""Fetch MOM pages as '#'-headed text: python scripts/fetch_mom.py (from repo root)."""
import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class FetchError(Exception):
    pass


_DROP = ["nav", "footer", "aside", "script", "style"]
_BLOCKS = {"h1", "h2", "h3", "h4", "p", "li", "tr"}
_SKIP = _BLOCKS | {"ul", "ol", "table"}


def _guard(line: str) -> str:
    """Strip leading '#' from body lines so chunk_text sees no spurious headings."""
    return line.lstrip("#").lstrip()


def _own_text(el) -> str:
    """Text of el excluding any nested block element (those are emitted separately)."""
    parts: list[str] = []

    def walk(node):
        for child in node.children:
            if isinstance(child, NavigableString):
                parts.append(str(child))
            elif child.name not in _SKIP:
                parts.append(" ")
                walk(child)
                parts.append(" ")

    walk(el)
    txt = _clean("".join(parts))
    return re.sub(r"\s+([.,;:!?])", r"\1", txt)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("div.page-content") or soup.body or soup
    for t in root.find_all(_DROP):
        t.decompose()
    cut = root.find(string=lambda s: isinstance(s, NavigableString) and "Share this page" in s)
    if cut is not None:
        node = cut
        while node is not root and node is not None:
            for sib in list(node.next_siblings):
                sib.extract()
            node = node.parent
        cut.extract()

    lines: list[str] = []
    for el in root.find_all(list(_BLOCKS)):
        if el.name in ("h1", "h2", "h3", "h4"):
            txt = _own_text(el)
            if txt:
                lines.append(f"# {txt}")
        elif el.name == "tr":
            cells = [_own_text(c) for c in el.find_all(["td", "th"]) if c.find_parent("tr") is el]
            cells = [c for c in cells if c]
            if cells:
                lines.append(_guard(" | ".join(cells)))
        else:
            txt = _own_text(el)
            if txt:
                lines.append(f"- {_guard(txt)}" if el.name == "li" else _guard(txt))
    return "\n".join(lines)


def fetch_page(url: str, get=requests.get) -> str:
    resp = get(url, timeout=20, headers={"User-Agent": "sg-contract-checker-capstone"})
    if resp.status_code != 200:
        raise FetchError(f"{url} returned HTTP {resp.status_code}")
    text = html_to_text(resp.text)
    if len(text) < 200:
        raise FetchError(
            f"{url} gave under 200 characters of text; page may be loaded by JavaScript; save it manually"
        )
    return text


def fetch_all(manifest_path: str, out_dir: str, get=requests.get) -> list[str]:
    entries = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    written = []
    for e in entries:
        if not e.get("fetch"):
            continue
        text = fetch_page(e["url"], get=get)
        (Path(out_dir) / e["file"]).write_text(text, encoding="utf-8")
        written.append(e["file"])
    return written


if __name__ == "__main__":
    for name in fetch_all("data/knowledge_base/sources.json", "data/knowledge_base"):
        n = len((Path("data/knowledge_base") / name).read_text(encoding="utf-8"))
        print(f"{name}: {n} characters")
