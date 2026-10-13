"""LLM adapter. The agent depends on the LLM protocol; GroqLLM is the production client."""

from dataclasses import dataclass, field
from typing import Protocol

from groq import APIError, APITimeoutError, BadRequestError, Groq

from app.config import settings


class LLMError(Exception):
    pass


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON text from the model


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0

    def as_message(self) -> dict:
        msg: dict = {"role": "assistant", "content": self.content or ""}
        if self.tool_calls:
            msg["tool_calls"] = [
                {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
                for c in self.tool_calls
            ]
        return msg


class LLM(Protocol):
    model: str

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse: ...


class GroqLLM:
    def __init__(self, model: str | None = None, timeout: float = 45.0):
        self.model = model or settings.GROQ_MODEL
        # The SDK retries 429s using the server's retry-after hint (free tier: 8k tokens/min).
        self._client = Groq(api_key=settings.GROQ_API_KEY, timeout=timeout, max_retries=4)

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        try:
            try:
                r = self._create(messages, tools, temperature=0)
            except BadRequestError as e:
                # The model sometimes emits a tool call Groq can't parse. Sampling once more,
                # slightly off zero temperature, is a cheap second chance before failing the run.
                if _code(e) not in ("output_parse_failed", "tool_use_failed"):
                    raise
                r = self._create(messages, tools, temperature=0.3)
        except APITimeoutError:
            raise LLMError("The AI service timed out") from None
        except APIError as e:
            raise LLMError(f"The AI service failed: {e}") from None
        m = r.choices[0].message
        return LLMResponse(
            content=m.content or "",
            tool_calls=[ToolCall(c.id, c.function.name, c.function.arguments or "{}") for c in (m.tool_calls or [])],
            tokens_in=getattr(r.usage, "prompt_tokens", 0) or 0,
            tokens_out=getattr(r.usage, "completion_tokens", 0) or 0,
        )

    def _create(self, messages: list[dict], tools: list[dict], temperature: float):
        return self._client.chat.completions.create(
            model=self.model, messages=messages, tools=tools, tool_choice="auto",
            temperature=temperature, max_tokens=2048,
        )


def _code(err: BadRequestError) -> str:
    body = err.body if isinstance(err.body, dict) else {}
    return (body.get("error") or body).get("code", "") if isinstance(body, dict) else ""
