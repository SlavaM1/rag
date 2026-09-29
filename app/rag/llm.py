from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from .config import Settings


class LLMError(Exception):
    """A safe error that can be shown to an API client."""


class LLMConfigurationError(LLMError):
    pass


class LLMAuthenticationError(LLMError):
    pass


class LLMRateLimitError(LLMError):
    pass


class LLMTimeoutError(LLMError):
    pass


class LLMUnavailableModelError(LLMError):
    pass


class LLMUnavailableError(LLMError):
    pass


class LLMInvalidResponseError(LLMError):
    pass


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    finish_reason: str | None = None


class LLMProvider(Protocol):
    async def generate(self, messages: list[dict[str, str]], model: str) -> LLMResponse:
        """Generate one non-streaming Chat Completions response."""


class DeepSeekProvider:
    """Official DeepSeek OpenAI-compatible Chat Completions adapter."""

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url
        self.temperature = settings.deepseek_temperature
        self.max_tokens = settings.deepseek_max_tokens
        self.timeout_seconds = settings.deepseek_timeout_seconds

    async def generate(self, messages: list[dict[str, str]], model: str) -> LLMResponse:
        if not self.api_key:
            raise LLMConfigurationError("DEEPSEEK_API_KEY is not configured")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            # Keep baseline and RAG comparable: no hidden reasoning-token budget.
            "thinking": {"type": "disabled"},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("DeepSeek request timed out") from exc
        except httpx.RequestError as exc:
            raise LLMUnavailableError("DeepSeek is currently unavailable") from exc

        if response.status_code in {401, 403}:
            raise LLMAuthenticationError("DeepSeek authentication failed")
        if response.status_code == 429:
            raise LLMRateLimitError("DeepSeek rate limit reached; try again later")
        if response.status_code in {400, 404}:
            raise LLMUnavailableModelError("The selected DeepSeek model is unavailable")
        if response.is_error:
            raise LLMUnavailableError("DeepSeek could not complete the request")

        try:
            data: dict[str, Any] = response.json()
            choice = data["choices"][0]
            content = choice["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("missing message content")
            usage = data.get("usage") or {}
            if not isinstance(usage, dict):
                usage = {}
            return LLMResponse(
                content=content.strip(),
                model=data.get("model") if isinstance(data.get("model"), str) else model,
                prompt_tokens=_optional_int(usage.get("prompt_tokens")),
                completion_tokens=_optional_int(usage.get("completion_tokens")),
                total_tokens=_optional_int(usage.get("total_tokens")),
                finish_reason=choice.get("finish_reason") if isinstance(choice.get("finish_reason"), str) else None,
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMInvalidResponseError("DeepSeek returned an invalid response") from exc


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None
