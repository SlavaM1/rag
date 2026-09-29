---
title: Обзор mcp-ai
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Обзор mcp-ai

## Назначение

`mcp-ai` — демонстрационное чат-приложение с сохранением диалогов, OpenAI-совместимой LLM и динамически обнаруживаемыми MCP tools. Пользователь работает с Angular-интерфейсом, backend передаёт вопрос модели, а модель решает, нужно ли вызвать доступный MCP tool.

Текущая поставка содержит один MCP server: `weather-mcp`. `weather-mcp` получает погоду от `wttr.in`, умеет сохранять измерения и запускать периодический сбор. Отдельного Currency MCP в репозитории нет.

## Основные технологии

### Frontend

Angular 20.3, standalone component `App`, Angular signals и `HttpClient`. Production-сборку раздаёт nginx. Исходники находятся в `frontend/src/app/`.

### Backend

FastAPI 0.116 в `backend/app/main.py`, SQLAlchemy 2 и Alembic. Класс `ChatAgent` из `backend/app/agent.py` организует LLM и MCP tool calls.

### Хранилища

PostgreSQL 17 хранит чат-сессии и сообщения. Локальный SQLite-файл `weather.db` внутри `weather-mcp` хранит weather schedules и weather samples. Эти хранилища не заменяют друг друга.

### LLM и MCP

`OpenAICompatibleClient` отправляет запросы в OpenAI-compatible `/chat/completions`. `MCPToolsClient` открывает MCP 2.2 Streamable HTTP-сессию, вызывает `list_tools()` и `call_tool()`.

## Подсистемы

### Чат и сессии

`ChatSession` и `ChatMessage` в `backend/app/models.py` сохраняют историю. Пользователь может создать сессию, выбрать прежнюю сессию и отправлять в неё новые сообщения.

### Агент

`ChatAgent.run(...)` добавляет `SYSTEM_PROMPT`, сохранённую историю и новый вопрос в LLM messages. Модель получает schema инструментов текущей MCP-сессии и сама выбирает обычный ответ или tool call.

### Weather MCP

`weather-mcp/weather_mcp/server.py` публикует `/mcp` и `/health`. MCP server регистрирует восемь tools: текущая погода, прогноз, почасовая погода, управление расписаниями и сводка накопленных измерений.

### Инфраструктура

`docker-compose.yml` запускает `frontend`, `backend`, `weather-mcp` и `db`. Named volumes сохраняют PostgreSQL и SQLite-данные между обычными остановками Compose.

## Поддерживаемые пользовательские сценарии

- Обычный разговор с настроенной LLM без вызова MCP tool.
- Запрос текущей погоды, прогноза или почасовых данных для города.
- Создание, просмотр и остановка фонового периодического сбора погоды.
- Немедленное сохранение одного weather sample и получение агрегации за период.
- Продолжение сохранённой беседы с передачей всей сохранённой user/assistant history модели.

## Текущее состояние

Проект реализует request-scoped LLM/MCP orchestration и persistence чатов. Нет authentication, authorization, multi-user isolation, streaming LLM response, очереди запросов, RAG/embeddings, отдельной state machine и нескольких одновременно настроенных MCP servers. `docs/day16.md` содержит историческое описание прежнего DeepWiki этапа и не соответствует текущей runtime-конфигурации.

## High-level request flow

### Обычный ответ

```text
User
→ Angular App
→ nginx /api/
→ FastAPI POST /api/sessions/{session_id}/messages
→ ChatAgent
→ OpenAICompatibleClient
→ LLM
→ FastAPI и PostgreSQL
→ Angular App
→ User
```

### Ответ с MCP tool

```text
User
→ Angular App
→ FastAPI
→ ChatAgent открывает MCP ClientSession
→ ClientSession.list_tools()
→ LLM с function tools
→ выбранный weather-mcp tool
→ wttr.in или SQLite/APScheduler
→ результат tool как LLM tool message
→ LLM формирует итоговый текст
→ FastAPI сохраняет ChatMessage.mcp_data в PostgreSQL
→ Angular App показывает текст и технические tool calls
→ User
```
