from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
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
    provider: str | None = None
    metrics: dict[str, int | float | str | bool | None] = field(default_factory=dict)
    provider_metrics: dict[str, object] = field(default_factory=dict)


class LLMProvider(Protocol):
    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate one non-streaming Chat Completions response."""


class DeepSeekProvider:
    """Official DeepSeek OpenAI-compatible Chat Completions adapter."""

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url
        self.temperature = settings.deepseek_temperature
        self.max_tokens = settings.deepseek_max_tokens
        self.timeout_seconds = settings.deepseek_timeout_seconds

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        if not self.api_key:
            raise LLMConfigurationError("DEEPSEEK_API_KEY is not configured")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
            # Keep baseline and RAG comparable: no hidden reasoning-token budget.
            "thinking": {"type": "disabled"},
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
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
            extra_usage = {
                key: value
                for key, value in usage.items()
                if key not in {"prompt_tokens", "completion_tokens", "total_tokens"}
                and isinstance(value, (str, int, float, bool))
            }
            return LLMResponse(
                content=content.strip(),
                model=data.get("model") if isinstance(data.get("model"), str) else model,
                prompt_tokens=_optional_int(usage.get("prompt_tokens")),
                completion_tokens=_optional_int(usage.get("completion_tokens")),
                total_tokens=_optional_int(usage.get("total_tokens")),
                finish_reason=choice.get("finish_reason") if isinstance(choice.get("finish_reason"), str) else None,
                provider="deepseek",
                provider_metrics={"usage": extra_usage} if extra_usage else {},
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMInvalidResponseError("DeepSeek returned an invalid response") from exc


class OllamaProvider:
    """Ollama's native non-streaming chat adapter."""

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.base_url = settings.ollama_base_url
        self.default_model = settings.ollama_default_model
        self.temperature = settings.ollama_temperature
        self.max_tokens = settings.ollama_max_tokens
        self.timeout_seconds = settings.ollama_timeout_seconds
        self.transport = transport

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        requested_model = model or self.default_model
        payload: dict[str, object] = {
            "model": requested_model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {
                "temperature": self.temperature if temperature is None else temperature,
                "num_predict": self.max_tokens if max_tokens is None else max_tokens,
            },
        }
        if json_mode:
            payload["format"] = "json"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, transport=self.transport) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError("Ollama request timed out") from exc
        except httpx.RequestError as exc:
            raise LLMUnavailableError("Ollama is currently unavailable") from exc

        if response.status_code in {401, 403}:
            raise LLMAuthenticationError("Ollama authentication failed")
        if response.status_code == 429:
            raise LLMRateLimitError("Ollama rate limit reached; try again later")
        if response.status_code == 404:
            raise LLMUnavailableModelError("The selected Ollama model is unavailable")
        if response.is_error:
            raise LLMUnavailableError("Ollama could not complete the request")

        try:
            data: dict[str, Any] = response.json()
            message = data["message"]
            content = message["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("missing message content")
            prompt_tokens = _optional_int(data.get("prompt_eval_count"))
            completion_tokens = _optional_int(data.get("eval_count"))
            total_tokens = (
                prompt_tokens + completion_tokens
                if prompt_tokens is not None and completion_tokens is not None
                else None
            )
            total_duration_ms = _nanoseconds_to_milliseconds(data.get("total_duration"))
            load_duration_ms = _nanoseconds_to_milliseconds(data.get("load_duration"))
            prompt_duration_ms = _nanoseconds_to_milliseconds(data.get("prompt_eval_duration"))
            eval_duration_ms = _nanoseconds_to_milliseconds(data.get("eval_duration"))
            prompt_rate = _tokens_per_second(prompt_tokens, prompt_duration_ms)
            generation_rate = _tokens_per_second(completion_tokens, eval_duration_ms)
            metrics: dict[str, int | float | str | bool | None] = {
                "prompt_eval_count": prompt_tokens,
                "eval_count": completion_tokens,
                "input_tokens": prompt_tokens,
                "output_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "total_duration_ms": total_duration_ms,
                "load_duration_ms": load_duration_ms,
                "prompt_eval_duration_ms": prompt_duration_ms,
                "eval_duration_ms": eval_duration_ms,
                "prompt_tokens_per_second": prompt_rate,
                "generation_tokens_per_second": generation_rate,
            }
            provider_metrics: dict[str, object] = {}
            for key in ("created_at", "done", "done_reason"):
                value = data.get(key)
                if isinstance(value, (str, bool)):
                    provider_metrics[key] = value
            return LLMResponse(
                content=content.strip(),
                model=data.get("model") if isinstance(data.get("model"), str) else requested_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                finish_reason=data.get("done_reason") if isinstance(data.get("done_reason"), str) else None,
                provider="ollama",
                metrics=metrics,
                provider_metrics=provider_metrics,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise LLMInvalidResponseError("Ollama returned an invalid response") from exc


class LLMProviderFactory:
    """Create only the provider selected for the current request."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create(self, provider: str) -> LLMProvider:
        if provider == "ollama":
            return OllamaProvider(self.settings)
        if provider == "deepseek":
            return DeepSeekProvider(self.settings)
        raise ValueError("provider must be ollama or deepseek")


class MeasuredLLMProvider:
    """Collect aggregate metrics without retaining prompt or response text."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self.calls: list[dict[str, object]] = []

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        started = perf_counter()
        prompt_chars = sum(len(message.get("content", "")) for message in messages)
        options: dict[str, float | int] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["max_tokens"] = max_tokens
        try:
            response = await self.provider.generate(
                messages,
                model,
                json_mode=json_mode,
                **options,
            )
        except Exception as exc:
            self.calls.append(
                {
                    "latency_ms": round((perf_counter() - started) * 1000, 2),
                    "prompt_chars": prompt_chars,
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "total_tokens": None,
                    "metrics": {},
                    "provider_metrics": {"error_type": type(exc).__name__},
                }
            )
            raise
        self.calls.append(
            {
                "latency_ms": round((perf_counter() - started) * 1000, 2),
                "prompt_chars": prompt_chars,
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_tokens": response.total_tokens,
                "metrics": response.metrics,
                "provider_metrics": response.provider_metrics,
            }
        )
        return response

    def metrics(self) -> dict[str, object]:
        prompt_tokens = _sum_available(self.calls, "prompt_tokens")
        completion_tokens = _sum_available(self.calls, "completion_tokens")
        reported_total = _sum_available(self.calls, "total_tokens")
        total_tokens = reported_total
        if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
            total_tokens = prompt_tokens + completion_tokens
        prompt_duration_ms = _sum_nested_available(self.calls, "prompt_eval_duration_ms")
        eval_duration_ms = _sum_nested_available(self.calls, "eval_duration_ms")
        return {
            "llm_latency_ms": round(sum(float(call["latency_ms"]) for call in self.calls), 2),
            "total_prompt_chars": sum(int(call["prompt_chars"]) for call in self.calls),
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "prompt_tokens_per_second": _tokens_per_second(prompt_tokens, prompt_duration_ms),
            "generation_tokens_per_second": _tokens_per_second(completion_tokens, eval_duration_ms),
            "provider_specific": {
                "calls": [
                    {**dict(call["metrics"]), **dict(call["provider_metrics"])}
                    for call in self.calls
                ]
            },
        }


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _nanoseconds_to_milliseconds(value: object) -> float | None:
    duration = _optional_int(value)
    return round(duration / 1_000_000, 3) if duration is not None else None


def _tokens_per_second(tokens: int | None, duration_ms: float | None) -> float | None:
    if tokens is None or duration_ms is None or duration_ms <= 0:
        return None
    return round(tokens / (duration_ms / 1000), 3)


def _sum_available(calls: list[dict[str, object]], key: str) -> int | None:
    if not calls:
        return None
    values = [call.get(key) for call in calls]
    if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
        return None
    return sum(int(value) for value in values)


def _sum_nested_available(calls: list[dict[str, object]], key: str) -> float | None:
    if not calls:
        return None
    values: list[float] = []
    for call in calls:
        metrics = call.get("metrics")
        if not isinstance(metrics, dict) or not isinstance(metrics.get(key), (int, float)):
            return None
        values.append(float(metrics[key]))
    return sum(values)
