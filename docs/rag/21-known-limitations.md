---
title: Известные ограничения
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Известные ограничения

## Known limitations

- Chat требует доступную OpenAI-compatible LLM с function calling и всеми тремя `LLM_*` settings.
- Погода зависит от wttr.in; fallback provider и project SLA отсутствуют.
- В конфигурации один `MCP_SERVER_URL`; реального multi-server discovery/routing нет.
- LLM и MCP connections request-scoped; streaming ответа и request queue отсутствуют.
- History полностью передаётся модели без token/context management.
- Frontend не имеет routing, test suite, streaming UI, session deletion/rename или identity UI.
- Weather schedules выполняются в одном `weather-mcp` process; scheduler jobs не persistent сами по себе.

## Technical debt

- `Settings.database_url` code default использует password `mcp_ai`, тогда как Compose/.env.example default — `mcp_ai_local`; Compose environment явно сглаживает различие внутри containers.
- `WeatherRepository` выполняет собственную additive SQLite migration без version table и Alembic.
- `ChatSession.messages` сортирует одинаковые `created_at` дополнительно по role, поэтому chronology в точности timestamp может зависеть от enum sort.
- Обычный agent endpoint сохраняет discovery в `available_tools`, но Angular template отображает cards только для legacy `mcp_data.tools`.
- `SessionCreate.title` и `ToolListRequest.message` проходят min length до handler `.strip()`, поэтому whitespace-only input может сохраниться как empty string в этих legacy/create paths.

## Not implemented

- Authentication, authorization и multi-user isolation.
- RAG runtime, embeddings, vector database, retrieval и agent personalization.
- Persistent agent state machine, task recovery и job queue.
- Currency MCP, Open-Meteo integration, отдельный geocoding provider и multiple configured MCP servers.
- LLM provider registry, model catalog, token usage/finish reason presentation, `max_tokens`, stop sequences, reasoning effort.

## Potential improvements

Это предложения, а не реализованные возможности.

- Ввести authentication, authorization и user-scoped sessions.
- Добавить context truncation/summarization и token accounting.
- Создать MCP server registry, explicit tool policy и health aggregation.
- Версионировать SQLite schema и формализовать recovery semantics schedules.
- Добавить real integration, API failure, frontend и security tests.
- Настроить TLS, secret management и structured redaction для deployment вне local network.
