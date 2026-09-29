# Chunking Strategy Comparison

## Dataset

Documents: 26
Words: 9084
Queries: 15

## Fixed Size

chunk_size: 1000
overlap: 150
chunks: 102
average size: 885.71
min size: 149
max size: 1000

## Structural

max_chunk_size: 1500
overlap: 150
chunks: 357
average size: 219.76
min size: 6
max size: 1497

## Evaluation

| Metric | Fixed | Structural |
|---|---:|---:|
| Hit@1 | 0.333 | 0.533 |
| Hit@3 | 0.667 | 0.800 |
| Hit@5 | 0.800 | 0.867 |

## Queries

### Query 1

Из каких сервисов и хранилищ состоит архитектура mcp-ai?

Expected files: 01-architecture.md, 00-overview.md

Fixed results:

1. README.md | mcp-ai Knowledge Base | score 0.6911
2. 00-overview.md | Обзор mcp-ai | score 0.6875
3. 06-mcp-architecture.md | MCP архитектура | score 0.6758
4. 21-known-limitations.md | Известные ограничения | score 0.6356
5. 07-mcp-tools.md | Каталог MCP tools | score 0.5955

Structural results:

1. 06-mcp-architecture.md | MCP архитектура | score 0.791
2. 00-overview.md | Обзор mcp-ai > Назначение | score 0.6751
3. 24-glossary.md | Глоссарий > MCP server | score 0.6652
4. 00-overview.md | Обзор mcp-ai | score 0.6569
5. 07-mcp-tools.md | Каталог MCP tools | score 0.6549

### Query 2

Как FastAPI сохраняет успешный или ошибочный обмен с агентом?

Expected files: 03-backend.md

Fixed results:

1. 14-api.md | HTTP API | score 0.4751
2. 02-project-structure.md | Структура проекта | score 0.4626
3. 19-error-handling.md | Обработка ошибок и logging | score 0.4608
4. 00-overview.md | Обзор mcp-ai | score 0.4494
5. 03-backend.md | Backend FastAPI | score 0.4311

Structural results:

1. 03-backend.md | Backend FastAPI | score 0.5495
2. 01-architecture.md | Архитектура > FastAPI backend | score 0.4921
3. 03-backend.md | Backend FastAPI > HTTP handlers > Сообщение агенту | score 0.4631
4. 14-api.md | HTTP API > GET `/api/sessions/{session_id}` > Path parameter | score 0.4477
5. 14-api.md | HTTP API > Формат и базовый адрес | score 0.4393

### Query 3

Какое состояние Angular интерфейса блокируется во время отправки сообщения?

Expected files: 04-frontend.md

Fixed results:

1. 04-frontend.md | Angular frontend | score 0.4892
2. 14-api.md | HTTP API | score 0.4212
3. 04-frontend.md | Angular frontend | score 0.3821
4. 01-architecture.md | Архитектура | score 0.3422
5. 03-backend.md | Backend FastAPI | score 0.3378

Structural results:

1. 04-frontend.md | Angular frontend | score 0.6461
2. 00-overview.md | Обзор mcp-ai > Основные технологии > Frontend | score 0.5854
3. 00-overview.md | Обзор mcp-ai > High-level request flow > Обычный ответ | score 0.5494
4. 05-llm-integration.md | Интеграция с LLM > Token usage и finish reason | score 0.5132
5. 12-memory-and-history.md | Память и история диалога > Sessions | score 0.4869

### Query 4

Какие настройки LLM обязательны и какой endpoint использует клиент?

Expected files: 05-llm-integration.md

Fixed results:

1. 01-architecture.md | Архитектура | score 0.6505
2. 05-llm-integration.md | Интеграция с LLM | score 0.6178
3. 17-running-project.md | Запуск проекта | score 0.6068
4. 12-memory-and-history.md | Память и история диалога | score 0.5489
5. 21-known-limitations.md | Известные ограничения | score 0.5466

Structural results:

1. 17-running-project.md | Запуск проекта > Требования | score 0.6426
2. 01-architecture.md | Архитектура > LLM boundary | score 0.629
3. 05-llm-integration.md | Интеграция с LLM > Клиент | score 0.6222
4. 16-configuration.md | Конфигурация > LLM > `LLM_API_KEY` | score 0.5781
5. 03-backend.md | Backend FastAPI > Dependencies > `get_llm_client()` | score 0.5728

### Query 5

Как MCP tools обнаруживаются и ограничиваются текущей server session?

Expected files: 06-mcp-architecture.md

Fixed results:

1. 00-overview.md | Обзор mcp-ai | score 0.7187
2. 00-overview.md | Обзор mcp-ai | score 0.7182
3. 21-known-limitations.md | Известные ограничения | score 0.7092
4. 06-mcp-architecture.md | MCP архитектура | score 0.6979
5. 12-memory-and-history.md | Память и история диалога | score 0.6972

Structural results:

1. 06-mcp-architecture.md | MCP архитектура > Несколько MCP servers | score 0.7594
2. 24-glossary.md | Глоссарий > MCP server | score 0.7574
3. 00-overview.md | Обзор mcp-ai > Текущее состояние | score 0.7418
4. 23-use-cases.md | Пользовательские сценарии > Multi-MCP request | score 0.7348
5. 01-architecture.md | Архитектура > MCP boundary | score 0.7197

### Query 6

Какие восемь инструментов предоставляет Weather MCP?

Expected files: 07-mcp-tools.md

Fixed results:

1. 08-weather-mcp.md | Weather MCP | score 0.6743
2. 00-overview.md | Обзор mcp-ai | score 0.6464
3. 02-project-structure.md | Структура проекта | score 0.6184
4. 00-overview.md | Обзор mcp-ai | score 0.5949
5. 09-scheduler-mcp.md | Scheduler MCP | score 0.5845

Structural results:

1. 00-overview.md | Обзор mcp-ai > Подсистемы > Weather MCP | score 0.7758
2. 08-weather-mcp.md | Weather MCP | score 0.7674
3. 16-configuration.md | Конфигурация > Weather MCP | score 0.7262
4. 24-glossary.md | Глоссарий > MCP tool | score 0.7005
5. 16-configuration.md | Конфигурация > Сеть и порты > `WEATHER_MCP_PORT` | score 0.6397

### Query 7

Какие ошибки weather provider возвращает Weather MCP и есть ли fallback?

Expected files: 08-weather-mcp.md

Fixed results:

1. 08-weather-mcp.md | Weather MCP | score 0.69
2. 08-weather-mcp.md | Weather MCP | score 0.6433
3. 07-mcp-tools.md | Каталог MCP tools | score 0.6278
4. 00-overview.md | Обзор mcp-ai | score 0.6049
5. 19-error-handling.md | Обработка ошибок и logging | score 0.5924

Structural results:

1. 08-weather-mcp.md | Weather MCP | score 0.729
2. 19-error-handling.md | Обработка ошибок и logging > Weather provider errors | score 0.6848
3. 16-configuration.md | Конфигурация > Weather MCP | score 0.6714
4. 18-testing.md | Тестирование > Automated tests > Weather MCP unittest | score 0.6319
5. 00-overview.md | Обзор mcp-ai > Подсистемы > Weather MCP | score 0.606

### Query 8

Как APScheduler восстанавливает weather schedules после перезапуска?

Expected files: 09-scheduler-mcp.md

Fixed results:

1. 02-project-structure.md | Структура проекта | score 0.6844
2. 09-scheduler-mcp.md | Scheduler MCP | score 0.5942
3. README.md | mcp-ai Knowledge Base | score 0.5827
4. 10-orchestration.md | Orchestration и multi-tool flows | score 0.5716
5. 09-scheduler-mcp.md | Scheduler MCP | score 0.5516

Structural results:

1. 24-glossary.md | Глоссарий > Scheduler | score 0.7234
2. 09-scheduler-mcp.md | Scheduler MCP > Доступные scheduling tools | score 0.7227
3. 22-data-flows.md | Потоки данных > Scheduler request | score 0.6572
4. 02-project-structure.md | Структура проекта > `weather-mcp/` > `weather_mcp/scheduler.py` и `persistence.py` | score 0.6529
5. 09-scheduler-mcp.md | Scheduler MCP > Восстановление после restart | score 0.6519

### Query 9

Какой лимит у multi-tool execution и выполняются ли вызовы последовательно?

Expected files: 10-orchestration.md

Fixed results:

1. 10-orchestration.md | Orchestration и multi-tool flows | score 0.6116
2. 10-orchestration.md | Orchestration и multi-tool flows | score 0.5936
3. 10-orchestration.md | Orchestration и multi-tool flows | score 0.5785
4. 22-data-flows.md | Потоки данных | score 0.5417
5. 06-mcp-architecture.md | MCP архитектура | score 0.4953

Structural results:

1. 10-orchestration.md | Orchestration и multi-tool flows > Ограничение и защита от loop | score 0.6077
2. 22-data-flows.md | Потоки данных > Запрос с несколькими MCP tools | score 0.5987
3. 10-orchestration.md | Orchestration и multi-tool flows > Реальные multi-tool сценарии | score 0.5679
4. 10-orchestration.md | Orchestration и multi-tool flows | score 0.5644
5. 10-orchestration.md | Orchestration и multi-tool flows > Последовательность нескольких tool calls | score 0.5606

### Query 10

Что хранится в ChatMessage.mcp_data и какая база данных его использует?

Expected files: 11-database.md

Fixed results:

1. 01-architecture.md | Архитектура | score 0.656
2. 10-orchestration.md | Orchestration и multi-tool flows | score 0.6427
3. 12-memory-and-history.md | Память и история диалога | score 0.6403
4. 00-overview.md | Обзор mcp-ai | score 0.6398
5. 22-data-flows.md | Потоки данных | score 0.6309

Structural results:

1. 01-architecture.md | Архитектура > Persistence > PostgreSQL | score 0.6921
2. 04-frontend.md | Angular frontend > Типы данных | score 0.6886
3. 14-api.md | HTTP API > POST `/api/sessions/{session_id}/messages` > Назначение | score 0.6701
4. 24-glossary.md | Глоссарий > JSONB | score 0.6558
5. 24-glossary.md | Глоссарий > Message | score 0.6348

### Query 11

Чем отличаются PostgreSQL с Alembic и SQLite в проекте?

Expected files: 11-database.md

Fixed results:

1. 11-database.md | База данных | score 0.6733
2. 21-known-limitations.md | Известные ограничения | score 0.5796
3. README.md | mcp-ai Knowledge Base | score 0.5388
4. 11-database.md | База данных | score 0.5223
5. 24-glossary.md | Глоссарий | score 0.4957

Structural results:

1. 24-glossary.md | Глоссарий > Migration | score 0.6224
2. 11-database.md | База данных > Обзор хранилищ | score 0.6215
3. 00-overview.md | Обзор mcp-ai > Основные технологии > Хранилища | score 0.6136
4. 12-memory-and-history.md | Память и история диалога > Долговременная память | score 0.6006
5. 01-architecture.md | Архитектура > Persistence > PostgreSQL | score 0.5787

### Query 12

Как запустить Docker Compose и какие volume сохраняют данные?

Expected files: 15-docker.md, 17-running-project.md

Fixed results:

1. 00-overview.md | Обзор mcp-ai | score 0.5146
2. 15-docker.md | Docker и Compose | score 0.4823
3. 09-scheduler-mcp.md | Scheduler MCP | score 0.436
4. README.md | mcp-ai Knowledge Base | score 0.3931
5. 18-testing.md | Тестирование | score 0.3922

Structural results:

1. 15-docker.md | Docker и Compose | score 0.5961
2. 15-docker.md | Docker и Compose > Volumes | score 0.529
3. 17-running-project.md | Запуск проекта > Остановка и persistence | score 0.5196
4. 17-running-project.md | Запуск проекта > Запуск через Docker | score 0.4687
5. 15-docker.md | Docker и Compose > Полный запуск | score 0.4504

### Query 13

Какие значения и диапазоны у MAX_TOOL_CALLS и MCP_TIMEOUT_SECONDS?

Expected files: 16-configuration.md

Fixed results:

1. 16-configuration.md | Конфигурация | score 0.748
2. 16-configuration.md | Конфигурация | score 0.6817
3. 23-use-cases.md | Пользовательские сценарии | score 0.5443
4. 07-mcp-tools.md | Каталог MCP tools | score 0.5374
5. 22-data-flows.md | Потоки данных | score 0.5102

Structural results:

1. 16-configuration.md | Конфигурация > MCP > `MCP_TIMEOUT_SECONDS` | score 0.8009
2. 16-configuration.md | Конфигурация > LLM > `LLM_TIMEOUT_SECONDS` | score 0.6821
3. 07-mcp-tools.md | Каталог MCP tools > Источник tools > `get_weather_summary` | score 0.6582
4. 16-configuration.md | Конфигурация > Weather MCP > `WEATHER_HTTP_TIMEOUT_SECONDS` | score 0.6361
5. 16-configuration.md | Конфигурация > LLM > `MAX_TOOL_CALLS` | score 0.5681

### Query 14

Какие риски безопасности связаны с secrets, CORS, TLS и MCP tools?

Expected files: 20-security.md

Fixed results:

1. README.md | mcp-ai Knowledge Base | score 0.5699
2. 21-known-limitations.md | Известные ограничения | score 0.4555
3. 20-security.md | Безопасность | score 0.4492
4. 07-mcp-tools.md | Каталог MCP tools | score 0.432
5. 19-error-handling.md | Обработка ошибок и logging | score 0.4222

Structural results:

1. 20-security.md | Безопасность | score 0.5983
2. 21-known-limitations.md | Известные ограничения > Potential improvements | score 0.5221
3. 18-testing.md | Тестирование > Coverage limits | score 0.4463
4. 01-architecture.md | Архитектура > Границы ответственности | score 0.4422
5. 02-project-structure.md | Структура проекта > `weather-mcp/` > `weather_mcp/server.py` | score 0.4408

### Query 15

Опиши поток scheduled weather collection от запроса до SQLite.

Expected files: 22-data-flows.md, 23-use-cases.md

Fixed results:

1. README.md | mcp-ai Knowledge Base | score 0.7429
2. 02-project-structure.md | Структура проекта | score 0.7393
3. 11-database.md | База данных | score 0.7107
4. 10-orchestration.md | Orchestration и multi-tool flows | score 0.6505
5. 09-scheduler-mcp.md | Scheduler MCP | score 0.6458

Structural results:

1. 00-overview.md | Обзор mcp-ai > Основные технологии > Хранилища | score 0.7489
2. 11-database.md | База данных > SQLite Weather MCP | score 0.7484
3. 02-project-structure.md | Структура проекта > `weather-mcp/` > `weather_mcp/scheduler.py` и `persistence.py` | score 0.7446
4. 22-data-flows.md | Потоки данных > Scheduler request | score 0.7286
5. 01-architecture.md | Архитектура > Persistence > SQLite | score 0.7229

## Observations

Scores and Hit@K values above are generated from the recorded document-level relevance set. Results can differ after changing the embedding model, chunk parameters, or documentation corpus.
