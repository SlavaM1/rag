---
title: Память и история диалога
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Память и история диалога

## Conversation history

История диалога — persisted `ChatMessage` записи PostgreSQL, связанные с `ChatSession`. Backend получает session через `_load_session(...)` в `backend/app/main.py`; `_session_query(...)` загружает relationship `messages` через `selectinload`.

`ChatSession.messages` упорядочены SQLAlchemy выражением `(ChatMessage.created_at, ChatMessage.role.asc())`. `ChatAgent.run(history, user_content)` передаёт в LLM все сохранённые messages с roles `user` и `assistant` и новый question. Records с `system` role из БД агент намеренно исключает.

## Sessions

`POST /api/sessions` создаёт `ChatSession`. `GET /api/sessions` возвращает summary с `message_count`, `GET /api/sessions/{session_id}` — session и messages. Angular `App` загружает summaries и выбранную полную session.

## Сохранение сообщений

`_save_exchange(...)` в `backend/app/main.py` сохраняет user content и assistant content одним commit. Assistant message хранит technical `mcp_data`, включая вызовы MCP. При ошибке агента handler тоже сохраняет пару user/assistant с ошибкой до отправки HTTP failure.

## Short-term и working memory

В рамках одного `ChatAgent.run(...)` short-term state — list `messages`, list executed `calls`, current discovered tools и открытая MCP session. Tool result добавляется в `messages` с role `tool`; следующая LLM iteration видит result.

## Долговременная память

Долговременная semantic memory отдельного агента отсутствует. PostgreSQL history — единственный persistent conversational context. SQLite weather data — domain history погоды, а не memory профиля пользователя.

## Context window

Код не ограничивает число сообщений, токены или последние N сообщений. `ChatAgent` передаёт всю доступную user/assistant history в каждый LLM request. Если provider context limit будет превышен, код не выполняет truncation или summarization; ошибка попадёт в LLM error flow.

## Not implemented / planned

### Summary

Автоматическое summary старой history не реализовано.

### Sticky facts и personalization

Sticky facts, user profile, preferences и персонализация не реализованы.

### Embeddings и RAG

Код не создаёт embeddings, vector store или retrieval pipeline. Каталог `docs/rag/` предназначен для будущей внешней RAG-индексации, но сам runtime `mcp-ai` RAG не использует.
