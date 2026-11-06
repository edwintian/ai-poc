import openai
from pydantic import BaseModel

from src.config import get_secret

# ADR 0014: each use case has its own model, chosen from real-model evals on 2026-11-06.
DEFAULT_MODEL = "gpt-4o-mini"  # Contract Health Check: 0 unsafe Consistent, best status accuracy
DEFAULT_QA_MODEL = "gpt-5.4-mini"  # Ask Your Contract: answered 15/15 on-topic, refused 3/3 off-topic


class LLMError(Exception):
    pass


def _api_error(action: str, e: Exception) -> LLMError:
    """Fixed sentence plus exception type and HTTP status only: never exception or prompt text."""
    status = getattr(e, "status_code", None)
    detail = f"{type(e).__name__}" + (f", HTTP status {status}" if status else "")
    return LLMError(f"The language model request failed while {action} ({detail}).")


class OpenAIClient:
    def __init__(self, client=None, model: str | None = None,
                 setting: str = "LLM_MODEL", default: str = DEFAULT_MODEL):
        self._client = client
        self.model = model or get_secret(setting) or default

    @classmethod
    def for_qa(cls, client=None) -> "OpenAIClient":
        """Ask Your Contract client: QA_LLM_MODEL, else DEFAULT_QA_MODEL (not LLM_MODEL)."""
        return cls(client=client, setting="QA_LLM_MODEL", default=DEFAULT_QA_MODEL)

    def _sdk(self):
        if self._client is None:
            key = get_secret("OPENAI_API_KEY")
            if not key:
                raise LLMError("OPENAI_API_KEY is not set; add it to the environment or secrets.")
            self._client = openai.OpenAI(api_key=key)
        return self._client

    @staticmethod
    def _messages(system: str, user: str) -> list[dict]:
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def complete(self, system: str, user: str, max_tokens: int = 2000) -> str:
        client = self._sdk()
        try:
            resp = client.chat.completions.create(
                model=self.model, messages=self._messages(system, user), max_tokens=max_tokens
            )
        except openai.OpenAIError as e:
            raise _api_error("generating a response", e) from e
        content = resp.choices[0].message.content
        if not content or not content.strip():
            raise LLMError("The language model returned an empty response.")
        return content

    def structured(self, system: str, user: str, model_cls: type[BaseModel]) -> BaseModel:
        client = self._sdk()
        try:
            resp = client.chat.completions.parse(
                model=self.model, messages=self._messages(system, user), response_format=model_cls
            )
        except openai.OpenAIError as e:
            raise _api_error("generating a structured response", e) from e
        except Exception:
            # Schema-invalid output (pydantic ValidationError) embeds input snippets; do not chain it.
            raise LLMError("The language model returned a malformed structured result.") from None
        message = resp.choices[0].message
        if getattr(message, "refusal", None):
            raise LLMError("The language model declined to answer this request.")
        if message.parsed is None:
            raise LLMError("The language model returned no structured result.")
        return message.parsed


def complete_structured(llm, system: str, user: str, model_cls: type[BaseModel]) -> BaseModel:
    return llm.structured(system, user, model_cls)
