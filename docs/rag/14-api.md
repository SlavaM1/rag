---
title: HTTP API
project: mcp-ai
document_type: technical_documentation
source: repository
---

# HTTP API

## Формат и базовый адрес

FastAPI application находится в `backend/app/main.py`. При Compose backend опубликован на `http://localhost:${BACKEND_PORT:-8000}`; Angular обращается к относительному `/api/...`. Interactive OpenAPI UI доступен как `/docs` по стандартному FastAPI behavior.

## GET `/health`

### Назначение

Проверяет PostgreSQL командой `SELECT 1` и показывает наличие трёх LLM settings. MCP server не проверяется.

### Response `200`

```json
{"status":"ok","database":"connected","llm":"configured"}
```

`llm` может быть `not_configured`.

### Ошибки

`503` с `{"detail":"База данных недоступна."}` при `SQLAlchemyError`.

## POST `/api/sessions`

### Назначение

Создаёт persisted chat session через `create_session(...)`.

### Request

```json
{"title":"Погода"}
```

`title` — string от 1 до 160, default `Новый MCP-чат`.

### Response `201`

Возвращает `SessionRead`: UUID/id, title, timestamps, `message_count`, пустой `messages`.

### Ошибки

`422` для Pydantic validation; `503` с `Не удалось создать чат-сессию.` при DB error.

## GET `/api/sessions`

### Назначение

`list_sessions(...)` возвращает summaries, отсортированные `updated_at DESC`.

### Response `200`

Массив `SessionSummary`: `id`, `title`, `created_at`, `updated_at`, `message_count`.

### Ошибки

`503` с `Не удалось загрузить чат-сессии.` при SQLAlchemy error.

## GET `/api/sessions/{session_id}`

### Назначение

Возвращает одну session и всю history через `_load_session(...)`.

### Path parameter

`session_id` — UUID. Некорректный UUID валидируется FastAPI.

### Response `200`

`SessionRead` с messages. Каждый message содержит `role`, `content`, optional JSON `mcp_data`, timestamp.

### Ошибки

`404` с `Чат-сессия не найдена.` для отсутствующей UUID session; `422` для invalid UUID.

## GET `/api/mcp/status`

### Назначение

Открывает MCP session и делает live `list_tools()`.

### Response `200`

```json
{
  "connected": true,
  "server_url": "http://weather-mcp:8001/mcp",
  "tool_count": 8,
  "error": null
}
```

При `MCPClientError` endpoint всё равно возвращает `200`, но `connected=false`, `tool_count=null` и text `error`.

## POST `/api/sessions/{session_id}/messages`

### Назначение

Запускает `ChatAgent` для natural-language message, сохраняет exchange и technical MCP metadata.

### Request

```json
{"message":"Какая сейчас погода в Новосибирске?"}
```

`message` trim-ится и после trim должен иметь длину 1–2000.

### Response `200`

```json
{
  "session": {"id":"<UUID>","messages":[]},
  "server_url":"http://weather-mcp:8001/mcp",
  "tool_calls": []
}
```

`session` — полный `SessionRead` уже с добавленными user/assistant messages. `tool_calls` содержит records с result/error/duration.

### Ошибки

`404` отсутствующая session; `422` invalid/blank message; `503` LLM configuration; `504` MCP timeout; `502` MCP unavailable, LLM unavailable, invalid LLM response или tool limit; `503` persistence failure. Error exchange пытается сохраниться до HTTP error response.

## POST `/api/sessions/{session_id}/tools/list`

### Назначение

Legacy direct discovery, не использует `ChatAgent`/LLM и не выполняет tools.

### Request

```json
{"message":"Получить список MCP-инструментов"}
```

Поле optional: default указан в `ToolListRequest`; длина 1–2000.

### Response `200`

`ToolListResponse`: `session`, normalized `tools`, `server_url`, `connected=true`. Assistant `mcp_data.tools` сохраняет list.

### Ошибки

`404` session отсутствует; `422` validation; `504` `MCPTimeoutError`; `502` прочие MCP errors; `503` ошибка записи exchange.
