import re
import subprocess
from pathlib import Path

import pytest

from src import config

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def no_dotenv(monkeypatch):
    monkeypatch.setattr(config, "_dotenv_loaded", True)  # don't read a real .env
    monkeypatch.delenv("X_SECRET", raising=False)


def test_env_wins_over_secrets(monkeypatch):
    monkeypatch.setenv("X_SECRET", " from-env ")
    monkeypatch.setattr(config.st, "secrets", {"X_SECRET": "from-secrets"})
    assert config.get_secret("X_SECRET") == "from-env"


def test_secrets_fallback(monkeypatch):
    monkeypatch.setattr(config.st, "secrets", {"X_SECRET": " from-secrets "})
    assert config.get_secret("X_SECRET") == "from-secrets"


def test_missing_everywhere(monkeypatch):
    monkeypatch.setattr(config.st, "secrets", {})
    assert config.get_secret("X_SECRET") is None


def test_whitespace_is_missing(monkeypatch):
    monkeypatch.setenv("X_SECRET", "   ")
    monkeypatch.setattr(config.st, "secrets", {"X_SECRET": "  "})
    assert config.get_secret("X_SECRET") is None


def test_gitignore_lists_secret_files():
    lines = (ROOT / ".gitignore").read_text().splitlines()
    assert ".env" in lines and ".streamlit/secrets.toml" in lines


def test_no_key_shaped_strings_in_repo():
    pattern = re.compile("s" + "k-[A-Za-z0-9_-]{20,}")
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout
    skip = (".git/", "myenv/", ".venv/", ".superpowers/")
    for rel in filter(None, out.split("\0")):
        if rel.startswith(skip):
            continue
        path = ROOT / rel
        if path.is_file():
            assert not pattern.search(path.read_text(errors="ignore")), rel
