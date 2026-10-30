import openai
import pytest
from pydantic import BaseModel, ValidationError

import src.llm as llm_mod
from src.llm import LLMError, OpenAIClient, complete_structured
from src.schemas import Finding, TermAssessment


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _resp(content=None, refusal=None, parsed=None):
    return _Obj(choices=[_Obj(message=_Obj(content=content, refusal=refusal, parsed=parsed))])


class StubSDK:
    def __init__(self, response=None, exc=None):
        self.response, self.exc, self.calls, self.parse_calls = response, exc, [], []
        self.chat = _Obj(completions=_Obj(create=self._create, parse=self._parse))

    def _create(self, **kw):
        self.calls.append(kw)
        if self.exc:
            raise self.exc
        return self.response

    def _parse(self, **kw):
        self.parse_calls.append(kw)
        if self.exc:
            raise self.exc
        return self.response


class Out(BaseModel):
    x: int


@pytest.fixture(autouse=True)
def no_real_secrets(monkeypatch):
    monkeypatch.setattr(llm_mod, "get_secret", lambda name: None)


def test_complete_returns_text_and_sends_request():
    sdk = StubSDK(_resp(content="hello"))
    out = OpenAIClient(client=sdk, model="m1").complete("SYS", "USR", max_tokens=123)
    assert out == "hello"
    call = sdk.calls[0]
    assert call["model"] == "m1" and call["max_tokens"] == 123
    assert call["messages"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "USR"},
    ]


def test_default_and_env_model(monkeypatch):
    assert OpenAIClient(client=StubSDK(_resp("a"))).model == "gpt-4o-mini"
    monkeypatch.setattr(llm_mod, "get_secret", lambda n: "gpt-x" if n == "LLM_MODEL" else None)
    assert OpenAIClient(client=StubSDK(_resp("a"))).model == "gpt-x"
    assert OpenAIClient(client=StubSDK(_resp("a")), model="explicit").model == "explicit"


@pytest.mark.parametrize("content", [None, "", "   "])
def test_complete_empty_content_raises(content):
    with pytest.raises(LLMError):
        OpenAIClient(client=StubSDK(_resp(content=content))).complete("s", "u")


def test_complete_openai_error_raises():
    with pytest.raises(LLMError):
        OpenAIClient(client=StubSDK(exc=openai.OpenAIError("boom"))).complete("s", "u")


def test_missing_api_key_names_variable_only():
    with pytest.raises(LLMError) as ei:
        OpenAIClient().complete("s", "u")
    assert "OPENAI_API_KEY" in str(ei.value)


def test_lazy_client_built_from_key(monkeypatch):
    built = {}

    class FakeOpenAI:
        def __init__(self, api_key):
            built["key"] = api_key
            self.chat = _Obj(completions=_Obj(create=lambda **kw: _resp("ok")))

    monkeypatch.setattr(llm_mod.openai, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(llm_mod, "get_secret", lambda n: "k" if n == "OPENAI_API_KEY" else None)
    c = OpenAIClient()
    assert built == {}
    assert c.complete("s", "u") == "ok"
    assert built["key"] == "k"


def test_structured_returns_parsed_and_passes_response_format():
    sdk = StubSDK(_resp(parsed=Out(x=3)))
    out = complete_structured(OpenAIClient(client=sdk, model="m"), "S", "U", Out)
    assert out == Out(x=3)
    call = sdk.parse_calls[0]
    assert call["response_format"] is Out and call["model"] == "m"
    assert call["messages"][0] == {"role": "system", "content": "S"}


def test_complete_structured_delegates_to_llm():
    class L:
        def structured(self, s, u, cls):
            return ("called", s, u, cls)

    assert complete_structured(L(), "s", "u", Out) == ("called", "s", "u", Out)


def test_structured_refusal_and_none_parsed():
    with pytest.raises(LLMError):
        OpenAIClient(client=StubSDK(_resp(refusal="no"))).structured("s", "u", Out)
    with pytest.raises(LLMError):
        OpenAIClient(client=StubSDK(_resp(parsed=None))).structured("s", "u", Out)


def test_structured_openai_error():
    with pytest.raises(LLMError):
        OpenAIClient(client=StubSDK(exc=openai.OpenAIError("x"))).structured("s", "u", Out)


class _StatusErr(openai.OpenAIError):
    status_code = 429


def test_error_message_never_leaks_exception_text_or_contract():
    fake_key = "sk-" + "A1b2C3d4" * 4
    phrase = "Distinctive Clause Zebra Moonbeam"
    exc = _StatusErr(f"bad key {fake_key} while reading {phrase}")
    for call in (
        lambda c: c.complete("system " + phrase, "user " + phrase),
        lambda c: c.structured("system", "user " + phrase, Out),
    ):
        with pytest.raises(LLMError) as ei:
            call(OpenAIClient(client=StubSDK(exc=exc)))
        msg = str(ei.value)
        assert fake_key not in msg and phrase not in msg and "bad key" not in msg
        assert "_StatusErr" in msg and "429" in msg
        assert ei.value.__cause__ is exc


def test_status_outside_three_values_rejected():
    with pytest.raises(ValidationError):
        TermAssessment(status="Bad", explanation="", reason="", question=None, source_ids=[])
    with pytest.raises(ValidationError):
        Finding(term="t", status="Bad", wording=None, page=None, explanation="", reason="",
                sources=[], question=None)
