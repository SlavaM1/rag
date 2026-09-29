---
title: MCP архитектура
project: mcp-ai
document_type: technical_documentation
source: repository
---

# MCP архитектура

## MCP client

`MCPToolsClient` в `backend/app/mcp_client.py` является MCP client backend. Он открывает `httpx2.AsyncClient`, `streamable_http_client`, затем `ClientSession`, вызывает `initialize()` и возвращает wrapper `ConnectedMCPTools`.

## MCP server

Единственный server текущего Compose — `weather-mcp` из `weather-mcp/weather_mcp/server.py`. `MCP_SERVER_URL` по умолчанию — `http://weather-mcp:8001/mcp`. Отдельный Currency MCP, multi-server registry и выбор одного из нескольких server URLs отсутствуют.

## Подключение

`MCPToolsClient.connect()` логирует `mcp_connecting`, открывает transport, логирует `mcp_connected` и закрывает context после завершения работы. `list_tools()` и `call_tool()` при прямом вызове открывают отдельную session. `ChatAgent.run(...)` держит одно подключение для discovery и всех tool calls одного chat turn.

## Discovery tools

`ConnectedMCPTools.list_tools()` ожидает поле `result.tools`, нормализует каждый tool через `_normalize_tool(...)` в `{name, description, input_schema}` и логирует `mcp_tools_listed`. Клиент принимает server fields `inputSchema` и `input_schema`.

## Передача schema LLM

`ChatAgent` преобразует discovery в OpenAI function schema. `allowed_tools` строится из list_tools текущей session, поэтому LLM не может выполнить tool name, не объявленный этим MCP server в текущем discovery result.

## Выполнение и возврат результата

`ConnectedMCPTools.call_tool(...)` нормализует MCP result к `is_error`, `content`, `structured_content`. `ChatAgent._execute_tool_call(...)` записывает duration, result/error, сериализует payload в JSON и добавляет LLM message с role `tool` и `tool_call_id`.

Если MCP result имеет `is_error=true`, `ChatAgent` не прекращает workflow автоматически: text из content становится error tool payload, после чего LLM может сформировать понятный ответ.

## Недоступность и timeout

`MCPToolsClient._raise_translated(...)` переводит timeout в `MCPTimeoutError`, MCP/Pydantic protocol problems в API-safe errors, прочие transport errors в `MCPConnectionError`. `ChatAgent` сопоставляет timeout с category `mcp_timeout`, остальные MCP errors — с `mcp_unavailable`.

## Несколько MCP servers

Код orchestration поддерживает несколько tool calls, но не несколько server connections. Единственный `MCPToolsClient` получает один URL из `Settings`, все discovered tools приходят из одной `ClientSession`.
