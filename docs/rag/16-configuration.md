---
title: Конфигурация
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Конфигурация

## Источники

`backend/app/config.py` определяет Pydantic `Settings` с `env_file=".env"`, `extra="ignore"`. Compose подставляет environment variables в containers. Weather MCP читает variables через `os.getenv` в `weather-mcp/weather_mcp/server.py`.

## PostgreSQL и backend

### `POSTGRES_DB`

**Где:** service `db` в `docker-compose.yml`. **Обязательность:** нет. **Default:** `mcp_ai`. **Назначение:** имя PostgreSQL БД. **Пример:** `POSTGRES_DB=mcp_ai`.

### `POSTGRES_USER`

**Где:** `db`. **Обязательность:** нет. **Default:** `mcp_ai`. **Назначение:** PostgreSQL user. **Пример:** `POSTGRES_USER=mcp_ai`.

### `POSTGRES_PASSWORD`

**Где:** `db`. **Обязательность:** для безопасного deployment да; Compose default `mcp_ai_local`. **Назначение:** пароль database user. **Пример:** `POSTGRES_PASSWORD=<SECRET>`.

### `DATABASE_URL`

**Где:** `Settings.database_url`, `backend/app/database.py`, Alembic и Compose backend/test. **Обязательность:** нет из-за code default. **Code default:** `postgresql+psycopg://mcp_ai:mcp_ai@db:5432/mcp_ai`. **Compose default:** URL с password `mcp_ai_local`. **Пример:** `postgresql+psycopg://mcp_ai:<SECRET>@db:5432/mcp_ai`.

### `CORS_ORIGINS`

**Где:** `Settings.cors_origins`, `main.py`. **Обязательность:** нет. **Default:** `http://localhost:4201`. **Формат:** comma-separated origins. **Пример:** `http://localhost:4201,https://example.test`.

## MCP

### `MCP_SERVER_URL`

**Где:** `Settings.mcp_server_url`, `get_mcp_client()`. **Обязательность:** нет. **Default:** `http://weather-mcp:8001/mcp`. **Назначение:** один Streamable HTTP MCP endpoint. **Пример:** `MCP_SERVER_URL=http://weather-mcp:8001/mcp`.

### `MCP_TIMEOUT_SECONDS`

**Где:** `Settings.mcp_timeout_seconds`, `MCPToolsClient`. **Обязательность:** нет. **Default:** `30.0`. **Validation:** `> 0`, `<= 120`. **Пример:** `MCP_TIMEOUT_SECONDS=30`.

## LLM

### `LLM_API_KEY`

**Где:** `Settings`, `OpenAICompatibleClient`. **Обязательность:** да для chat endpoint. **Default:** null. **Пример:** `LLM_API_KEY=<SECRET>`.

### `LLM_BASE_URL`

**Где:** `Settings`, `OpenAICompatibleClient.complete(...)`. **Обязательность:** да для chat. **Default:** null in code; `.env.example` uses `https://api.deepseek.com`. **Пример:** `LLM_BASE_URL=https://api.example.com`.

### `LLM_MODEL`

**Где:** `Settings`, LLM request `model`. **Обязательность:** да для chat. **Default:** null in code; `.env.example` uses `deepseek-chat`. **Пример:** `LLM_MODEL=provider-tool-model`.

### `LLM_TIMEOUT_SECONDS`

**Где:** `Settings`, `httpx2.Timeout`. **Обязательность:** нет. **Default:** `60.0`. **Validation:** `> 0`, `<= 300`. **Пример:** `LLM_TIMEOUT_SECONDS=60`.

### `MAX_TOOL_CALLS`

**Где:** `Settings`, `ChatAgent`. **Обязательность:** нет. **Default:** `4`. **Validation:** integer 1–20. **Пример:** `MAX_TOOL_CALLS=4`.

## Weather MCP

### `WEATHER_DATABASE_PATH`

**Где:** `WeatherRepository` creation in `server.py`. **Обязательность:** нет. **Default:** `/data/weather.db`. **Compose:** hardcoded `/data/weather.db`. **Пример:** `WEATHER_DATABASE_PATH=/data/weather.db`.

### `WEATHER_BASE_URL`

**Где:** `WttrWeatherClient`. **Обязательность:** нет. **Default:** `https://wttr.in`. **Назначение:** base URL единственного weather provider. **Пример:** `WEATHER_BASE_URL=https://wttr.in`.

### `WEATHER_HTTP_TIMEOUT_SECONDS`

**Где:** `_weather_timeout()`. **Обязательность:** нет. **Default/fallback:** `15`. Non-numeric или `<=0` также становится 15. **Пример:** `WEATHER_HTTP_TIMEOUT_SECONDS=15`.

## Сеть и порты

### `FRONTEND_PORT`

**Где:** Compose frontend port mapping. **Default:** `4201`. **Пример:** `FRONTEND_PORT=4201`.

### `BACKEND_PORT`

**Где:** Compose backend mapping. **Default:** `8000`. **Пример:** `BACKEND_PORT=8000`.

### `WEATHER_MCP_PORT`

**Где:** Compose weather-mcp mapping. **Default:** `8001`. **Пример:** `WEATHER_MCP_PORT=8001`.

## Proxy

### `HTTP_PROXY` и `HTTPS_PROXY`

**Где:** Compose backend/weather-mcp и `httpx2` clients с `trust_env=True`. **Обязательность:** нет. **Default:** пустая строка в Compose. **Пример:** `HTTP_PROXY=http://proxy.example:3128`.

### `NO_PROXY`

**Где:** Compose backend/weather-mcp. **Default:** `localhost,127.0.0.1,db,backend,frontend,weather-mcp` с Compose interpolation. **Назначение:** bypass proxy для internal hosts. **Пример:** `NO_PROXY=localhost,127.0.0.1,db,backend,frontend,weather-mcp`.
