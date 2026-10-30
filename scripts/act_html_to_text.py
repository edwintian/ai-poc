"""Convert a saved SSO Employment Act page: python scripts/act_html_to_text.py in.html out.txt"""
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def act_html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    sections = soup.select("div.prov1")
    if not sections:
        raise ValueError("no div.prov1 sections found")
    out: list[str] = []
    for sec in sections:
        hdr = sec.select_one("td.prov1Hdr")
        txt_td = sec.select_one("td.prov1Txt")
        number = ""
        if txt_td is not None and txt_td.find("strong"):
            strong = txt_td.find("strong")
            number = _clean(strong.get_text())
            strong.extract()
        heading = _clean(hdr.get_text(" ")) if hdr else ""
        out.append(f"# {number} {heading}".strip())
        if hdr is not None:
            hdr.decompose()
        for tr in sec.find_all("tr"):
            tr.insert_before(NavigableString("\n"))
        for td in sec.find_all("td"):
            td.insert_after(NavigableString(" "))
        for tbl in sec.find_all("table"):
            tbl.insert_after(NavigableString("\n"))
        for line in sec.get_text().split("\n"):
            line = _clean(line)
            if line:
                out.append(line)
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    text = act_html_to_text(Path(src).read_text(encoding="utf-8"))
    Path(dst).write_text(text, encoding="utf-8")
    print(f"{sum(1 for ln in text.splitlines() if ln.startswith('# '))} sections written")
