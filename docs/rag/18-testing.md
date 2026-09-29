---
title: Тестирование
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Тестирование

## Automated tests

### Backend pytest

Файлы находятся в `backend/tests/`: `test_mcp_client.py`, `test_agent.py`, `test_api.py`. `conftest.py` использует `DATABASE_URL` и после тестов удаляет созданные sessions.

- `test_mcp_client.py` проверяет discovery/normalization, connection error translation и tool result normalization.
- `test_agent.py` проверяет dynamic discovery → tool → final answer, no-tool response, запрет unadvertised tool и batch limit до partial execution.
- `test_api.py` проверяет session creation, whitespace message validation, persistence legacy tool list и agent exchange/tool payload.

### Weather MCP unittest

Файлы в `weather-mcp/tests/`: `test_weather.py`, `test_scheduler.py`.

- `test_weather.py` покрывает current/forecast/hourly normalization, URL encoding, optional fields, city not found, timeout, HTTP errors, malformed response, tool schemas/order, city validation и `/health`.
- `test_scheduler.py` покрывает minimum interval, duplicate/stop/persistence, recovery active schedules, immediate collection, normalized data, empty/aggregated summary и provider error без отключения job.

### Frontend

Frontend test files и `test` npm script отсутствуют. `docker compose build frontend` проверяет, что Angular production build собирается.

## Команды

```bash
docker compose --profile test run --build --rm backend-test
docker compose --profile test run --build --rm weather-mcp-test
docker compose build frontend
```

## Coverage limits

Нет зафиксированных live integration tests с реальными LLM/wttr.in, full MCP HTTP transport, real-time scheduler/misfire, всех API error paths, Alembic downgrade, security/auth, concurrency и load scenarios.

## Manual test scenarios

### Проверка обычного LLM запроса

Настройте LLM и создайте session. Отправьте вопрос, не требующий свежих данных. Ожидание: `POST /messages` возвращает assistant text, `tool_calls` пуст, два message records сохраняются.

### Проверка Weather MCP

Отправьте «Какая сейчас погода в Москве?». Ожидание: LLM выбирает `get_current_weather`, UI показывает tool call и final text; assistant `mcp_data.tool_calls` содержит normalized result.

### Проверка Scheduler MCP

Отправьте запрос на сбор каждые 60 секунд для города. Затем вызовите list/summary после ожидания. Ожидание: `create_weather_schedule`, weather SQLite schedule/sample persistence и summary.

### Проверка нескольких MCP tools

Отправьте вопрос про погоду нескольких городов или попросите несколько сведений, при tool-calling model. Ожидание: результат зависит от выбора LLM, но backend не исполняет более `MAX_TOOL_CALLS` и показывает все calls.

### Проверка persistence

Создайте чат и schedule, выполните `docker compose down`, затем `docker compose up -d`. Ожидание: session доступна PostgreSQL, active schedule зарегистрирован weather-mcp из SQLite.

### Проверка MCP failure

Остановите `weather-mcp` или задайте unreachable `MCP_SERVER_URL`. Ожидание: `/api/mcp/status` возвращает `connected=false`; agent endpoint возвращает mapped error и старается сохранить error exchange.
