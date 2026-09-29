---
title: Backend FastAPI
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Backend FastAPI

## Application

Реализация находится в `backend/app/main.py`. Объект `app` создаётся на module import; отдельных startup/shutdown handlers нет. Docker command сначала выполняет `alembic upgrade head`, затем запускает `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

## Dependencies

### `get_db()`

Функция `get_db()` в `backend/app/database.py` создаёт SQLAlchemy `SessionLocal` в context manager. `SessionLocal` использует `expire_on_commit=False`.

### `get_mcp_client()`

Функция `get_mcp_client()` в `backend/app/main.py` создаёт `MCPToolsClient(settings.mcp_server_url, settings.mcp_timeout_seconds)` на endpoint request.

### `get_llm_client()`

Функция `get_llm_client()` создаёт `OpenAICompatibleClient` из значений `Settings`.

## HTTP handlers

### Health

`health(...)` выполняет `SELECT 1` через PostgreSQL Session и возвращает состояние database и настройку LLM. MCP connectivity не входит в `/health`.

### Сессии

`create_session(...)`, `list_sessions(...)` и `get_session(...)` работают с `ChatSession`. `_session_query(...)` применяет `selectinload(ChatSession.messages)`, а `_session_read(...)` преобразует ORM objects в `SessionRead`.

### Сообщение агенту

`send_agent_message(...)` загружает session, создаёт `ChatAgent` и вызывает `await agent.run(chat_session.messages, user_content)`. Успешный и ошибочный exchange сохраняются `_save_exchange(...)` как user и assistant messages.

### Legacy tool discovery

`list_mcp_tools(...)` соответствует `POST /api/sessions/{session_id}/tools/list`. Handler вызывает только `client.list_tools()`, сохраняет tools в `mcp_data.tools` и не вызывает LLM или MCP tool.

## DTO и validation

`backend/app/schemas.py` использует Pydantic. `AgentMessageRequest.message` имеет `StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)`. `SessionCreate.title` и `ToolListRequest.message` ограничены длиной, но handler дополнительно вызывает `.strip()`.

`MessageRead`, `SessionSummary`, `SessionRead`, `ToolDefinition`, `ToolListResponse`, `MCPStatus` и `AgentMessageResponse` определяют JSON API responses.

## Сохранение exchange

`_save_exchange(...)` меняет title первой пустой session на первые 157 символов `user_content` и `...` при большей длине. Затем добавляет `ChatMessage` с roles `user` и `assistant`, задаёт `updated_at = func.now()` и commit. Любой `SQLAlchemyError` вызывает rollback и HTTP 503.

## CORS

`CORSMiddleware` получает `settings.allowed_origins`; значение `CORS_ORIGINS` разбивается по запятым. Разрешены methods `GET`, `POST`, `OPTIONS`, любые headers, `allow_credentials=False`.

## Бизнес-слои

В backend отсутствуют классы repository/service и отдельные FastAPI routers. `ChatAgent`, `OpenAICompatibleClient`, `MCPToolsClient` и SQLAlchemy models являются основными выделенными единицами логики.
