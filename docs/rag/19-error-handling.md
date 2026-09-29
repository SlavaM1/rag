---
title: Обработка ошибок и logging
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Обработка ошибок и logging

## LLM errors

`backend/app/llm_client.py` определяет `LLMConfigurationError`, `LLMUnavailableError`, `LLMInvalidResponseError` от base `LLMError`.

- Missing settings: configuration error.
- `httpx2.TimeoutException`: `LLM не ответила за отведённое время.`
- HTTP status: text содержит HTTP code, но не response body.
- `httpx2.RequestError`: connection message.
- Invalid JSON/`choices[0].message`: invalid response.

`ChatAgent.run(...)` преобразует их в categories, а `send_agent_message(...)` возвращает configuration как 503, unavailable/invalid как 502.

## MCP errors

`backend/app/mcp_client.py` определяет `MCPConnectionError`, `MCPTimeoutError`, `MCPInvalidResponseError`. `_raise_translated(...)` рекурсивно ищет timeout в `BaseExceptionGroup`, преобразует Pydantic validation/MCP protocol errors в safe messages и скрывает нераспознанную transport detail.

Agent mapping: timeout → HTTP 504; other MCP client errors → 502. `/api/mcp/status` перехватывает `MCPClientError` и отдаёт `200` status payload с `connected=false`.

## Tool errors

`ChatAgent._execute_tool_call(...)` не вызывает MCP при malformed JSON arguments или tool name вне `allowed_tools`; error передаётся модели. MCP `is_error` превращается в text из `content` либо generic controlled tool error. Tool error не обязан прерывать agent loop.

## Weather provider errors

`weather-mcp/weather_mcp/weather.py` возвращает MCP `ToolError` с machine-readable JSON error code. Timeout, HTTP/network availability, city not found и invalid response имеют отдельные codes. Scheduled job ловит provider `Exception`, логирует и продолжает schedule.

## Database errors

`main.py` ловит `SQLAlchemyError` в health/create/list/save. `_save_exchange(...)` вызывает rollback и HTTP 503. `get_session` не перехватывает непредвиденную DB error отдельно.

SQLite `WeatherRepository` не оборачивает sqlite errors в custom exception, поэтому такие failures зависят от MCP/ASGI exception behavior.

## Validation errors

FastAPI/Pydantic возвращают стандартный 422 для invalid API DTO/path UUID. Weather MCP использует Pydantic schema и custom validation city. Bounds `days`, intervals и `minutes` находятся в `Field` declarations `server.py`.

## Backend logging

`backend/app/logging_utils.py` создаёт logger `mcp_ai.events` со stderr JSON without timestamp. `log_event(...)` записывает `event`, component и non-null fields. Events включают `mcp_connecting`, `mcp_connected`, `mcp_tools_listed`, `llm_tool_selected`, MCP call start/finish, tool limit и LLM error categories. Database persistence использует `logger.exception`.

## Weather logging

`weather-mcp/weather_mcp/logging_config.py` заменяет root handlers JSON formatter. Формат включает timestamp UTC, level, logger, message и optional event/provider/errorCategory/statusCode. `httpx2`/`httpcore2` понижены до WARNING, потому что request-line logs могут содержать user city query.
