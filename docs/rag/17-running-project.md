---
title: Запуск проекта
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Запуск проекта

## Требования

Для документированного способа запуска нужны Docker и Docker Compose. Для chat endpoint нужен OpenAI-compatible LLM с tool calling и три LLM environment variables.

## Подготовка `.env`

Создайте `.env` на основе `.env.example`, не добавляя реальные credentials в Git. Минимальная LLM конфигурация:

```dotenv
LLM_API_KEY=<SECRET>
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

Остальные defaults приведены в `.env.example` и `16-configuration.md`. `.env` исключён `.gitignore`.

## Запуск через Docker

Из корня репозитория:

```bash
docker compose up --build -d
docker compose ps
```

Compose запускает migration `alembic upgrade head` в backend перед FastAPI. Отдельно применять migration для нормального container launch не требуется.

## Проверка health

```bash
curl -sS http://localhost:8000/health
curl -sS http://localhost:8001/health
```

Frontend health URL: `http://localhost:4201/health`. Ответ frontend health даёт nginx, а не FastAPI.

## Адреса

- UI: `http://localhost:4201`
- Backend OpenAPI: `http://localhost:8000/docs`
- Backend health: `http://localhost:8000/health`
- Weather MCP health: `http://localhost:8001/health`
- Weather MCP endpoint: `http://localhost:8001/mcp`

## Первый API запрос

```bash
curl -sS -X POST http://localhost:8000/api/sessions \
  -H 'Content-Type: application/json' \
  -d '{"title":"Погода"}'
```

Подставьте UUID из ответа в запрос:

```bash
curl -sS -X POST http://localhost:8000/api/sessions/<SESSION_UUID>/messages \
  -H 'Content-Type: application/json' \
  -d '{"message":"Какая сейчас погода в Новосибирске?"}'
```

## Остановка и persistence

```bash
docker compose down
```

Нормальная остановка сохраняет named volumes с chats и weather SQLite. Не используйте `docker compose down -v`, если данные должны сохраниться.

## Локальные development commands

`frontend/package.json` содержит `npm run start` и `npm run build`. `npm run start` не включает proxy config; для API нужен отдельный reachable backend/CORS setup или Compose frontend.

Backend и weather-mcp Dockerfiles являются документированными executable paths. Отдельные non-Docker setup instructions, virtualenv scripts или Makefile в репозитории отсутствуют.
