---
title: Структура проекта
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Структура проекта

## Основные каталоги

```text
mcp-ai/
├── backend/
│   ├── app/
│   ├── alembic/
│   └── tests/
├── frontend/
│   └── src/app/
├── weather-mcp/
│   ├── weather_mcp/
│   └── tests/
├── docs/
│   └── rag/
├── docker-compose.yml
├── .env.example
└── README.md
```

## Корень репозитория

### `README.md`

Практическое описание текущего запуска, архитектуры, MCP tools и ограничений. Для фактов runtime приоритетнее исходный код и Compose.

### `docker-compose.yml`

Описывает production services, test profiles, ports, variables, healthchecks и named volumes.

### `.env.example`

Шаблон local/Compose configuration. Файл `.env` игнорируется через `.gitignore`; реальные значения секретов не должны попадать в документацию или Git.

## `backend/`

### `backend/app/`

Python package FastAPI: `main.py` содержит endpoints, `agent.py` — orchestration, `llm_client.py` — LLM client, `mcp_client.py` — MCP client, `models.py` — SQLAlchemy models, `schemas.py` — Pydantic DTO, `database.py` — engine/session dependency.

### `backend/alembic/`

Alembic environment и migration `versions/20260921_01_create_chat_tables.py`.

### `backend/tests/`

pytest tests backend API, `ChatAgent` и `MCPToolsClient`.

## `frontend/`

### `frontend/src/app/`

Единственный root component `App`, HTML/SCSS template и `ApiService`. Отдельных component, routing и model directories нет.

### Build files

`angular.json`, `package.json`, `tsconfig*.json`, `Dockerfile`, `nginx.conf` определяют сборку и production serving.

## `weather-mcp/`

### `weather_mcp/server.py`

MCP server, lifespan, validation input и восемь MCP tool functions.

### `weather_mcp/weather.py`

`WttrWeatherClient`, `WeatherService`, Pydantic result models и нормализация ответа wttr.in.

### `weather_mcp/scheduler.py` и `persistence.py`

`WeatherScheduler` запускает APScheduler; `WeatherRepository` хранит schedules/samples в SQLite.

### `weather-mcp/tests/`

unittest tests weather parsing, server schemas, scheduling и SQLite persistence.

## `docs/`

`docs/day16.md` — историческая сводка предыдущего этапа, не источник актуального runtime behavior. `docs/rag/` содержит документацию для дальнейшей RAG-индексации.
