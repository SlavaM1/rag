---
title: Интеграция с LLM
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Интеграция с LLM

## Клиент

`OpenAICompatibleClient` в `backend/app/llm_client.py` реализует единственный LLM provider adapter. Отдельных provider classes, provider registry или списка моделей в коде нет. Значения `LLM_BASE_URL` и `LLM_MODEL` позволяют использовать OpenAI-compatible API; `.env.example` показывает `https://api.deepseek.com` и `deepseek-chat`.

## Обязательная конфигурация

`ensure_configured()` требует непустые `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`. При отсутствии поднимается `LLMConfigurationError` с именами missing variables. Backend превращает ошибку в HTTP 503 для agent endpoint.

## Формирование запроса

### Endpoint и headers

`complete(...)` делает `POST {LLM_BASE_URL.rstrip('/')}/chat/completions`, передаёт `Authorization: Bearer {LLM_API_KEY}` и `Content-Type: application/json`.

### JSON body

```json
{
  "model": "LLM_MODEL",
  "messages": "system, history, user, tool messages",
  "tools": "динамически найденные MCP function definitions",
  "tool_choice": "auto",
  "temperature": 0.2
}
```

`max_tokens`, stop sequences, reasoning effort, provider-specific parameters, seed и token counting не передаются и не обрабатываются текущим кодом.

## System prompt и history

`SYSTEM_PROMPT` в `backend/app/agent.py` предписывает отвечать по-русски, учитывать историю, использовать tools только для актуальных/внешних данных, не показывать сырой JSON и не придумывать данные.

`ChatAgent.run(...)` добавляет `SYSTEM_PROMPT`, затем все сохранённые `ChatMessage` только с `MessageRole.USER` или `MessageRole.ASSISTANT`, затем новый user message. `system` messages из БД не отправляются LLM. Ограничение context window, last N messages и summarization отсутствуют.

## Tool definitions

`ChatAgent._to_llm_tool(...)` конвертирует каждый discovered MCP tool в OpenAI function format с `name`, `description` и `parameters`. Если description/schema отсутствуют, применяются `MCP tool` и пустой JSON object schema.

## Tool-call loop

LLM response должен содержать `choices[0].message` с text content и/или list `tool_calls`. При tool calls `ChatAgent` добавляет assistant tool-call message, выполняет calls, добавляет `role: tool` JSON result и вызывает LLM снова. Цикл завершается только непустым final text без tool calls.

## Token usage и finish reason

`OpenAICompatibleClient` не читает и не сохраняет response `usage`, `prompt_tokens`, `completion_tokens`, `total_tokens` или `finish_reason`. Angular UI не отображает token usage, provider и model.

## HTTP client и proxy

`httpx2.AsyncClient` использует timeout `LLM_TIMEOUT_SECONDS` и `trust_env=True`, поэтому учитывает стандартные `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` environment variables.

## Ошибки LLM

`httpx2.TimeoutException`, `HTTPStatusError` и `RequestError` становятся `LLMUnavailableError`; malformed JSON/response structure становятся `LLMInvalidResponseError`. Подробности — в `19-error-handling.md`.
