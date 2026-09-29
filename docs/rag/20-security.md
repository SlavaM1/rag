---
title: Безопасность
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Безопасность

## Секреты

`LLM_API_KEY` читается environment settings и передаётся только в `Authorization: Bearer` request к LLM. `.env` внесён в `.gitignore`, а `.dockerignore` исключает `.env` из root Docker build context. Документация и `.env.example` используют `<SECRET>` вместо реального ключа.

`POSTGRES_PASSWORD` — credential PostgreSQL. Compose default предназначен для local environment, не для production secret management. `DATABASE_URL` может содержать пароль и должен храниться как secret.

## Proxy credentials

`HTTP_PROXY` и `HTTPS_PROXY` могут включать credentials. Compose передаёт их backend/weather-mcp, а `httpx2` использует `trust_env=True`. Такие URLs нельзя включать в committed configuration или logs.

## Сетевые границы

Compose публикует frontend/backend/weather-mcp ports на host; PostgreSQL не публикуется. nginx proxy направляет только `/api/` в backend. Weather MCP `/mcp` опубликован наружу default port mapping и не имеет authentication.

## Authentication и authorization

Authentication, authorization, user accounts и tenant isolation не реализованы. Любой сетевой клиент с доступом к API может создавать sessions, читать known UUID sessions и отправлять messages. Weather MCP tools также не требуют credential.

## Риски MCP tool execution

Backend разрешает вызов только names, discovered в current MCP session, что защищает от arbitrary tool name. Однако LLM сама выбирает аргументы и до `MAX_TOOL_CALLS` calls. Текущие bundled tools ограничены weather HTTP и SQLite schedules, но смена `MCP_SERVER_URL` на другой server меняет доступные capabilities без policy/allowlist на уровне tools.

## Внешние сервисы

User city и conversation history уходят в настроенный LLM provider; city также уходит wttr.in при weather requests. Проект не содержит consent flow, data retention policy или PII redaction.

## Логирование данных

Backend structured events не добавляют API key. Weather logging намеренно снижает verbosity HTTP client logs для сокращения риска вывода city URL. Но отсутствует системная redaction middleware и access log weather-mcp включён в `__main__.py`; не следует считать полную защиту пользовательских данных реализованной.

## CORS и transport

Backend CORS ограничен configurable `CORS_ORIGINS`, credentials отключены. TLS termination не реализован в Compose/nginx config: production TLS должен обеспечиваться внешним reverse proxy или инфраструктурой.
