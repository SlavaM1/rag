---
title: Индекс базы знаний mcp-ai
project: mcp-ai
document_type: technical_documentation_index
source: repository
---

# mcp-ai Knowledge Base

## Documents

- [Обзор](00-overview.md) — назначение, текущие возможности, подсистемы и high-level request flow.
- [Архитектура](01-architecture.md) — границы компонентов, связи frontend/backend/LLM/MCP/БД/Docker.
- [Структура проекта](02-project-structure.md) — назначение ключевых каталогов и файлов репозитория.
- [Backend](03-backend.md) — FastAPI application, dependencies, DTO и persistence handlers.
- [Frontend](04-frontend.md) — Angular `App`, `ApiService`, UI state и отображение MCP данных.
- [Интеграция с LLM](05-llm-integration.md) — OpenAI-compatible client, prompts, tools, параметры и ошибки.
- [MCP архитектура](06-mcp-architecture.md) — MCP client/session, discovery и выполнение tools.
- [Каталог MCP tools](07-mcp-tools.md) — каталог всех восьми tools `weather-mcp`.
- [Weather MCP](08-weather-mcp.md) — wttr.in integration, нормализация, HTTP/lifecycle и weather flow.
- [Scheduler MCP](09-scheduler-mcp.md) — APScheduler, SQLite schedules/samples и recovery.
- [Orchestration](10-orchestration.md) — `ChatAgent` loop, multi-tool sequence и ограничения.
- [База данных](11-database.md) — PostgreSQL SQLAlchemy schema, Alembic и weather SQLite schema.
- [Память и история](12-memory-and-history.md) — sessions, history context и отсутствующие memory/RAG features.
- [State machine агента](13-agent-state-machine.md) — отсутствие формальной state machine и фактический lifecycle.
- [API](14-api.md) — все backend HTTP endpoints, DTO и статусы ошибок.
- [Docker](15-docker.md) — Dockerfiles, Compose services, volumes, healthchecks и nginx proxy.
- [Конфигурация](16-configuration.md) — environment variables, defaults, constraints и formats.
- [Запуск проекта](17-running-project.md) — подготовка, Compose launch, health и первый запрос.
- [Тестирование](18-testing.md) — automated coverage, команды и manual scenarios.
- [Обработка ошибок](19-error-handling.md) — LLM/MCP/provider/DB errors и structured logging.
- [Безопасность](20-security.md) — secrets, network exposure, data flow и security gaps.
- [Известные ограничения](21-known-limitations.md) — ограничения, technical debt, отсутствующие возможности и improvements.
- [Потоки данных](22-data-flows.md) — пошаговые runtime flows и sequence diagram.
- [Пользовательские сценарии](23-use-cases.md) — реальные пользовательские сценарии и их components/tools.
- [Глоссарий](24-glossary.md) — термины в контексте `mcp-ai`.
