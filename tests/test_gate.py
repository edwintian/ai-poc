from pathlib import Path

import pytest
from streamlit.proto.TextInput_pb2 import TextInput as TextInputProto
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")
TITLES = {
    "pages/health_check.py": "Contract Health Check",
    "pages/ask_contract.py": "Ask Your Contract",
    "pages/about.py": "About Us",
    "pages/methodology.py": "Methodology",
}


@pytest.fixture
def at(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "pw")
    return AppTest.from_file(APP).run()


def test_initially_gated(at):
    assert len(at.text_input) == 1 and at.text_input[0].proto.type == TextInputProto.PASSWORD
    assert "authed" not in at.session_state or not at.session_state["authed"]


def test_bad_password(at):
    at.text_input[0].input("bad")
    at.button[0].click()
    at.run()
    assert len(at.error) == 1
    assert len(at.text_input) == 1
    assert "authed" not in at.session_state or not at.session_state["authed"]


def test_unconfigured_password(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    monkeypatch.setattr("src.config._dotenv_loaded", True)
    at = AppTest.from_file(APP).run()
    assert len(at.error) == 1 and not at.text_input


def test_good_password_and_pages(at):
    at.text_input[0].input("pw")
    at.button[0].click()
    at.run()
    assert at.session_state["authed"] is True
    assert not at.text_input
    assert at.title[0].value == "Contract Health Check"
    for page, title in list(TITLES.items())[1:]:
        at.switch_page(page).run()
        assert at.title[0].value == title
