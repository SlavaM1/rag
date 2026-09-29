---
title: Пользовательские сценарии
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Пользовательские сценарии

## Чат с LLM

### Пример запроса

`Объясни, что такое Model Context Protocol.`

### Компоненты

Angular `App`, FastAPI `ChatAgent`, `OpenAICompatibleClient`, PostgreSQL. Перед LLM всё равно выполняется MCP discovery, но tool может не вызываться.

### Результат

Пользователь получает assistant text. User/assistant exchange сохраняется в session.

## Weather request

### Пример запроса

`Какая сейчас погода в Москве?`

### Компоненты и tools

LLM может выбрать `get_current_weather`; backend, `weather-mcp`, `WttrWeatherClient` и wttr.in участвуют в цепочке.

### Результат

LLM формирует ответ из tool result. UI отображает final text и технический MCP call с JSON result.

## Forecast or hourly weather

### Пример запроса

`Покажи прогноз в Казани на три дня.` или `Какая погода по часам в Екатеринбурге?`

### Компоненты и tools

LLM может выбрать соответственно `get_weather_forecast` или `get_hourly_weather`.

### Результат

Формат зависит от final LLM text; raw normalized forecast/hourly result хранится в `mcp_data.tool_calls`.

## Scheduled weather monitoring

### Пример запроса

`Начни собирать погоду в Новосибирске каждую минуту.`

### Components and tools

При корректном model function calling LLM может вызвать `create_weather_schedule` с `interval_seconds: 60`. `WeatherScheduler` продолжает collection независимо от открытого browser/chat.

### Результат

Пользователь получает schedule identity/status; weather SQLite хранит schedule. Минимальный возможный interval — 30 seconds.

## Weather summary

### Пример запроса

`Дай сводку по Новосибирску за последний час.`

### Components and tools

LLM может вызвать `get_weather_summary(city, minutes)`. Для meaningful metrics необходимы ранее сохранённые samples: schedule или `run_weather_collection_now`.

### Результат

Summary содержит count, factual stored range и metrics; без samples tool возвращает message о пустом периоде.

## Conversation continuation

### Пример запроса

Откройте старую session в sidebar и отправьте новое сообщение.

### Компоненты

`App.selectSession(...)`, `GET /api/sessions/{id}`, PostgreSQL и `ChatAgent`.

### Результат

Backend передаёт persisted user/assistant history LLM. Это continuation history, не отдельная personalized memory feature.

## Multi-MCP request

Отдельный multi-MCP user scenario не поддержан, поскольку runtime настроен на один MCP server URL. Agent поддерживает несколько tool calls, но все они относятся к tools одного connected `weather-mcp` server.
