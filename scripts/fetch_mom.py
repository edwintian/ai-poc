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
            txt = _clean(el.get_text(" "))
            if txt:
                lines.append(f"# {txt}")
        elif el.name == "tr":
            cells = [_clean(c.get_text(" ")) for c in el.find_all(["td", "th"])]
            cells = [c for c in cells if c]
            if cells:
                lines.append(" | ".join(cells))
        else:
            if el.name == "p" and el.find_parent(["td", "th"]):
                continue
            txt = _clean(el.get_text(" "))
            if txt:
                lines.append(f"- {txt}" if el.name == "li" else txt)
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
