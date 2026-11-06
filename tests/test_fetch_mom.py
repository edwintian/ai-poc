import json
from pathlib import Path

import pytest

from scripts.fetch_mom import FetchError, fetch_all, fetch_page, html_to_text

FIXTURE = Path(__file__).parent / "fixtures" / "mini_mom.html"


class Resp:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code


def stub(text, status=200, calls=None):
    def get(url, **kwargs):
        if calls is not None:
            calls.append((url, kwargs))
        return Resp(text, status)

    return get


def test_html_to_text_structure():
    out = html_to_text(FIXTURE.read_text(encoding="utf-8"))
    lines = out.splitlines()
    assert "# Annual leave" in lines
    assert "# How much leave" in lines
    assert "- Leave is pro-rated for part years" in lines
    assert "1st | 7" in lines
    assert any("paid annual leave" in ln for ln in lines)
    for junk in ("NAVIGATION", "FOOTER", "SCRIPT TEXT", "trackingJunk", "Share this page", "RELATED LINKS"):
        assert junk not in out
    assert "\n\n" not in out


def test_fallback_to_body():
    html = "<html><body><nav>NAV</nav><h1>Title</h1><p>Body text</p></body></html>"
    out = html_to_text(html)
    assert "# Title" in out and "Body text" in out and "NAV" not in out


def test_fetch_page_ok_and_request_args():
    calls = []
    html = FIXTURE.read_text(encoding="utf-8")
    # ensure converted text is long enough
    text = fetch_page("http://x/y", get=stub(html, calls=calls))
    assert "# Annual leave" in text
    url, kw = calls[0]
    assert url == "http://x/y"
    assert kw["timeout"] == 20
    assert kw["headers"]["User-Agent"] == "sg-contract-checker-capstone"


def test_fetch_page_403():
    with pytest.raises(FetchError) as e:
        fetch_page("http://x/y", get=stub("", 403))
    assert "http://x/y" in str(e.value) and "403" in str(e.value)


def test_fetch_page_too_short():
    with pytest.raises(FetchError, match="JavaScript"):
        fetch_page("http://x/y", get=stub("<html><body><p>hi</p></body></html>"))


def test_fetch_all(tmp_path):
    manifest = tmp_path / "sources.json"
    manifest.write_text(json.dumps([
        {"file": "a.txt", "kind": "web", "title": "A", "url": "http://x/a", "fetch": True},
        {"file": "b.txt", "kind": "web", "title": "B", "url": "http://x/b", "fetch": False},
    ]))
    out = tmp_path / "out"
    out.mkdir()
    html = FIXTURE.read_text(encoding="utf-8")
    written = fetch_all(str(manifest), str(out), get=stub(html))
    assert written == ["a.txt"]
    assert (out / "a.txt").read_text(encoding="utf-8").startswith("# Annual leave")
    assert not (out / "b.txt").exists()


NESTED = """<html><body><div class="page-content"><h1>Title heading</h1>
<ul><li>Outer item alpha<ul><li>Inner item beta</li><li>Inner item gamma</li></ul></li></ul>
<table><tr><td>14</td><td>Type of leave, such as:<ul><li>Annual leave</li><li>Sick leave</li></ul></td></tr></table>
<p>See <a href="/x">the rules</a>.</p>
</div></body></html>"""


def test_nested_blocks_emitted_once():
    out = html_to_text(NESTED)
    for piece in ("Outer item alpha", "Inner item beta", "Inner item gamma",
                  "Annual leave", "Sick leave", "Type of leave"):
        assert out.count(piece) == 1, piece
    assert "- Outer item alpha" in out.splitlines()
    assert "- Inner item beta" in out.splitlines()
    assert "14 | Type of leave, such as:" in out.splitlines()
    assert "See the rules." in out.splitlines()


def test_leading_hash_guard():
    out = html_to_text('<html><body><div class="page-content"><h1>T</h1><p># not a heading</p>'
                       '<ul><li>## nor this</li></ul></div></body></html>')
    heads = [ln for ln in out.splitlines() if ln.startswith("#")]
    assert heads == ["# T"]
    assert "not a heading" in out and "nor this" in out
