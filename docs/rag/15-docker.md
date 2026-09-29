---
title: Docker и Compose
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Docker и Compose

## Compose services

`docker-compose.yml` определяет runtime `db`, `weather-mcp`, `backend`, `frontend` и profile `test` services `backend-test`, `weather-mcp-test`.

| Service | Image/build | Published port | Persistence |
| --- | --- | --- | --- |
| `db` | `postgres:17.6-alpine` | нет | `postgres_data:/var/lib/postgresql/data` |
| `weather-mcp` | `weather-mcp/Dockerfile`, `runtime` | `${WEATHER_MCP_PORT:-8001}:8001` | `weather_mcp_data:/data` |
| `backend` | `backend/Dockerfile`, `runtime` | `${BACKEND_PORT:-8000}:8000` | нет |
| `frontend` | `frontend/Dockerfile`, `runtime` | `${FRONTEND_PORT:-4201}:80` | нет |

## Volumes

`postgres_data` имеет explicit name `mcp-ai-postgres-data`; `weather_mcp_data` — `mcp-ai-weather-mcp-data`. Обычный `docker compose down` volumes сохраняет; `docker compose down -v` удаляет данные.

## Healthchecks и порядок

`db` использует `pg_isready`, weather-mcp/backend используют Python `urllib.request`, frontend — `wget` local `/health`. `backend` ждёт healthy `db` и `weather-mcp`; `frontend` ждёт healthy `backend`. `db` и `weather-mcp` не зависят друг от друга.

## `backend/Dockerfile`

Base — `python:3.12.11-slim`, requirements из `backend/requirements.txt`. Runtime command: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`. Test target добавляет dev requirements/tests и запускает Alembic plus pytest.

## `weather-mcp/Dockerfile`

Runtime base — `python:3.12-slim`; создаётся non-root `appuser` UID 10001 и writable `/data`. Command: `python -m weather_mcp`. Dockerfile содержит healthcheck, но Compose переопределяет его проверку/interval. Test target запускает `python -m unittest discover -s tests`.

## `frontend/Dockerfile`

Build stage `node:22.20.0-alpine` делает `npm ci` и `npm run build`. Runtime `nginx:1.29.1-alpine` копирует `/app/dist/mcp-ai/browser` и `frontend/nginx.conf`.

## nginx proxy

`frontend/nginx.conf` направляет `/api/` без переписывания URI на `http://backend:8000`; устанавливает Host/X-Forwarded-* headers, connect timeout 10s и read timeout 450s. `/health` отвечает `ok` локально; `/` использует SPA fallback `try_files`.

## Proxy variables

Compose передаёт `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` в backend/weather-mcp. `NO_PROXY` default включает local hosts и Compose service names. PostgreSQL и frontend proxy variables не получают.

## Полный запуск

```bash
docker compose up --build -d
docker compose ps
```

UI доступен на `http://localhost:4201`, backend — `http://localhost:8000`, weather MCP — `http://localhost:8001` по defaults.
