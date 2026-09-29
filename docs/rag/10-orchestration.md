---
title: Orchestration и multi-tool flows
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Orchestration и multi-tool flows

## Оркестратор

`ChatAgent` в `backend/app/agent.py` реализует orchestration одного `POST /api/sessions/{session_id}/messages`. Полноценного workflow engine, task queue или persistent orchestration state нет.

## Кто выбирает server и tool

### MCP server

Application code выбирает ровно один server URL: `Settings.mcp_server_url`. В текущем Compose это `weather-mcp`. LLM не выбирает server и backend не маршрутизирует между несколькими servers.

### MCP tool

LLM выбирает tool через OpenAI function calling после получения dynamically discovered schemas. Application code ограничивает выбор names, полученными в `allowed_tools` текущего `list_tools()`.

## Алгоритм `ChatAgent.run(...)`

1. `OpenAICompatibleClient.ensure_configured()` проверяет LLM config.
2. `MCPToolsClient.connect()` открывает одну MCP session на chat turn.
3. `mcp_session.list_tools()` формирует `tools`, `allowed_tools` и LLM function definitions.
4. `ChatAgent` строит messages: `SYSTEM_PROMPT`, persisted user/assistant history, new user message.
5. `OpenAICompatibleClient.complete(...)` вызывает LLM.
6. Если response не содержит tool calls и содержит непустой text, agent возвращает final `AgentResult`.
7. Если response содержит tool calls, agent проверяет лимит, добавляет assistant tool-call message, выполняет calls последовательно и добавляет tool messages.
8. Agent повторяет шаг 5, пока модель не вернёт final text или workflow не завершится error.

## Последовательность нескольких tool calls

Один LLM response может содержать batch tool calls. `ChatAgent` выполняет `normalized_calls` по порядку в `for`, помещая каждый result в messages. Следующий LLM call видит все results batch и может выбрать следующий tool. Поэтому результат tool A может использоваться моделью для выбора tool B на следующей итерации; application code не извлекает и не подставляет поля результата в аргументы B самостоятельно.

## Intermediate state

В памяти одного `run(...)` находятся `messages`, discovered `tools`, `allowed_tools`, `calls` и открытая MCP session. После завершения assistant `mcp_data` сохраняет `available_tools` и `tool_calls`; промежуточные LLM messages и internal loop state отдельно не сохраняются.

## Завершение и инварианты

Workflow успешен только при final nonempty string content без requested tool calls. Tool call должен содержать nonempty `id` и function `name`; arguments должны быть JSON object. Unadvertised tool не вызывается. MCP `is_error` превращается в LLM tool error message, но сам по себе не останавливает loop.

## Ограничение и защита от loop

`MAX_TOOL_CALLS` имеет default 4 и допустимый диапазон 1–20. Если весь следующий batch превышает remaining limit, `ChatAgent` выбрасывает `AgentExecutionError(category="tool_limit")` до частичного исполнения batch. Другого iteration limit или semantic loop detection нет.

## Ошибки в середине workflow

Некорректные JSON arguments и недоступное tool name становятся error record/tool message, поэтому LLM может отреагировать итогом. Ошибка MCP transport, timeout, LLM availability/invalid response или limit завершают `run(...)`. API handler сохраняет error exchange с category и уже выполненными calls, затем возвращает 502/503/504.

## Реальные multi-tool сценарии

### Создание наблюдения и сводка

LLM может вызвать `create_weather_schedule`, получить `schedule_id`, затем в последующих запросах вызвать `list_weather_schedules`, `run_weather_collection_now` или `get_weather_summary`. Накопление samples требует времени либо отдельного immediate collection; backend не принуждает такую последовательность.

### Несколько calls в одном turn

Код поддерживает несколько weather tools в одном response либо последовательных iterations, например получение current weather для нескольких городов. Конкретный набор calls не фиксирован: решение принадлежит LLM и ограничено dynamic discovery plus `MAX_TOOL_CALLS`.
