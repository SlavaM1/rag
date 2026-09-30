# Day 23 Retrieval Comparison

## Configuration

Embedding model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
Reranker: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (local CPU)
Similarity threshold: `0.4`
Candidate Top-K: `15`
Final Top-K: `5`

## Metrics

| Metric | Baseline | Enhanced |
|---|---:|---:|
| Hit@1 | 0.308 | 0.538 |
| Hit@3 | 0.538 | 0.615 |
| Hit@5 | 0.615 | 0.692 |

## Pipeline Metrics

Average candidates retrieved: 15.00
Average chunks after threshold: 13.62
Average final chunks: 5.00
Queries where reranking changed Top-1: 69.2%
Queries where reranking changed ordering: 100.0%
Average baseline retrieval time: 828.90 ms
Average rewrite time: 1318.45 ms
Average rerank time: 2116.27 ms
Average enhanced FAISS retrieval time: 25.89 ms

## Threshold Tuning

| Threshold | Average kept | Empty queries | Expected source retained |
|---|---:|---:|---:|
| 0.20 | 15.00 | 0.0% | 92.3% |
| 0.30 | 15.00 | 0.0% | 92.3% |
| 0.40 | 13.62 | 0.0% | 84.6% |
| 0.45 | 13.15 | 0.0% | 84.6% |
| 0.50 | 11.46 | 0.0% | 76.9% |

The configured threshold is selected from this small corpus-specific sweep by balancing retained expected sources against weak candidates; it must be revisited after changing the corpus, chunking, or embedding model.

## Questions

### q01

Original query: Какой HTTP path и transport использует Weather MCP server?

Rewritten query: Какой HTTP path и transport использует Weather MCP server?

Expected sources: 08-weather-mcp.md

Baseline retrieval:
1. 08-weather-mcp.md | Weather MCP > Назначение | score 0.7628
2. 08-weather-mcp.md | Weather MCP | score 0.6851
3. 20-security.md | Безопасность > Сетевые границы | score 0.6757
4. 00-overview.md | Обзор mcp-ai > Подсистемы > Weather MCP | score 0.6671
5. 16-configuration.md | Конфигурация > Weather MCP | score 0.6515

Enhanced retrieval:
1. 08-weather-mcp.md | Weather MCP > Назначение | similarity 0.7628 | rerank 5.351259708404541 | FAISS rank 1
2. 08-weather-mcp.md | Weather MCP > HTTP и lifecycle | similarity 0.6276 | rerank 4.768782138824463 | FAISS rank 9
3. 01-architecture.md | Архитектура > MCP boundary | similarity 0.6117 | rerank 3.5975217819213867 | FAISS rank 11
4. 16-configuration.md | Конфигурация > Сеть и порты > `WEATHER_MCP_PORT` | similarity 0.5952 | rerank 2.3659822940826416 | FAISS rank 13
5. 00-overview.md | Обзор mcp-ai > Подсистемы > Weather MCP | similarity 0.6671 | rerank 0.10022146999835968 | FAISS rank 4

### q02

Original query: Какие ограничения имеет параметр days у get_weather_forecast?

Rewritten query: Какие ограничения и допустимые значения имеет параметр days в функции get_weather_forecast?

Expected sources: 07-mcp-tools.md

Baseline retrieval:
1. 07-mcp-tools.md | Каталог MCP tools > Источник tools > `get_weather_forecast` | score 0.7142
2. 07-mcp-tools.md | Каталог MCP tools > Источник tools > `get_hourly_weather` | score 0.6033
3. 07-mcp-tools.md | Каталог MCP tools > Источник tools > `get_weather_summary` | score 0.5979
4. 23-use-cases.md | Пользовательские сценарии > Weather summary > Components and tools | score 0.5893
5. 08-weather-mcp.md | Weather MCP > Weather provider > Нормализация | score 0.5576

Enhanced retrieval:
1. 07-mcp-tools.md | Каталог MCP tools > Источник tools > `get_weather_forecast` | similarity 0.6877 | rerank 6.382916450500488 | FAISS rank 1
2. 07-mcp-tools.md | Каталог MCP tools > Источник tools > `get_hourly_weather` | similarity 0.5619 | rerank 3.170801877975464 | FAISS rank 4
3. 07-mcp-tools.md | Каталог MCP tools > Источник tools > `get_weather_summary` | similarity 0.5769 | rerank 1.3611257076263428 | FAISS rank 3
4. 08-weather-mcp.md | Weather MCP > Weather provider > Нормализация | similarity 0.5573 | rerank 1.3282757997512817 | FAISS rank 5
5. 07-mcp-tools.md | Каталог MCP tools > Источник tools > `create_weather_schedule` | similarity 0.5330 | rerank 0.009096731431782246 | FAISS rank 8

### q03

Original query: Где находятся FAISS индексы этого учебного RAG-проекта и когда они строятся?

Rewritten query: Где хранятся FAISS-индексы в учебном RAG-проекте и на каком этапе они создаются/строятся?

Expected sources: 15-docker.md

Baseline retrieval:
1. 02-project-structure.md | Структура проекта | score 0.5161
2. 17-running-project.md | Запуск проекта | score 0.4830
3. 24-glossary.md | Глоссарий > RAG | score 0.4364
4. 00-overview.md | Обзор mcp-ai > Текущее состояние | score 0.4296
5. 00-overview.md | Обзор mcp-ai | score 0.4225

Enhanced retrieval:
1. 12-memory-and-history.md | Память и история диалога > Not implemented / planned > Embeddings и RAG | similarity 0.4238 | rerank -6.861536502838135 | FAISS rank 5
2. 17-running-project.md | Запуск проекта | similarity 0.4740 | rerank -7.48986291885376 | FAISS rank 3
3. 24-glossary.md | Глоссарий > RAG | similarity 0.5035 | rerank -7.5040154457092285 | FAISS rank 2
4. 02-project-structure.md | Структура проекта | similarity 0.5519 | rerank -8.185079574584961 | FAISS rank 1
5. 00-overview.md | Обзор mcp-ai > Текущее состояние | similarity 0.4326 | rerank -8.391504287719727 | FAISS rank 4

### q04

Original query: Почему WeatherScheduler не воспроизводит пропущенные запуски после restart и как восстанавливаются active schedules?

Rewritten query: Почему WeatherScheduler не воспроизводит пропущенные запуски после restart и как восстанавливаются active schedules?

Expected sources: 09-scheduler-mcp.md

Baseline retrieval:
1. 09-scheduler-mcp.md | Scheduler MCP > Восстановление после restart | score 0.7672
2. 09-scheduler-mcp.md | Scheduler MCP > Доступные scheduling tools | score 0.6893
3. 22-data-flows.md | Потоки данных > Scheduler request | score 0.6723
4. 02-project-structure.md | Структура проекта > `weather-mcp/` > `weather_mcp/scheduler.py` и `persistence.py` | score 0.6702
5. 22-data-flows.md | Потоки данных > Application startup | score 0.6453

Enhanced retrieval:
1. 09-scheduler-mcp.md | Scheduler MCP > Восстановление после restart | similarity 0.7672 | rerank 8.911520957946777 | FAISS rank 1
2. 09-scheduler-mcp.md | Scheduler MCP > Доступные scheduling tools | similarity 0.6893 | rerank 0.9770286083221436 | FAISS rank 2
3. 22-data-flows.md | Потоки данных > Application startup | similarity 0.6453 | rerank 0.9269114136695862 | FAISS rank 5
4. 09-scheduler-mcp.md | Scheduler MCP > Хранение задач и результатов > `weather_schedules` | similarity 0.6222 | rerank -1.020094871520996 | FAISS rank 9
5. 09-scheduler-mcp.md | Scheduler MCP > Создание task | similarity 0.6321 | rerank -1.1729637384414673 | FAISS rank 7

### q05

Original query: Как проходит обычное сообщение пользователя от Angular UI до сохранения истории чата?

Rewritten query: Как проходит обычное сообщение пользователя от Angular UI до сохранения истории чата: поток данных и архитектура обработки сообщения, путь запроса от frontend Angular до backend, этапы обработки пользовательского сообщения, сохранение истории чата в базе данных, API-запросы и сервисы, участвующие в отправке и персистенции сообщений.

Expected sources: 22-data-flows.md, 04-frontend.md, 03-backend.md

Baseline retrieval:
1. 00-overview.md | Обзор mcp-ai > High-level request flow > Обычный ответ | score 0.5995
2. 12-memory-and-history.md | Память и история диалога > Sessions | score 0.5603
3. 00-overview.md | Обзор mcp-ai > Подсистемы > Чат и сессии | score 0.5371
4. 00-overview.md | Обзор mcp-ai > Основные технологии > Frontend | score 0.5251
5. 04-frontend.md | Angular frontend | score 0.5209

Enhanced retrieval:
1. 18-testing.md | Тестирование > Manual test scenarios > Проверка обычного LLM запроса | similarity 0.5193 | rerank 0.7593973278999329 | FAISS rank 9
2. 00-overview.md | Обзор mcp-ai > High-level request flow > Обычный ответ | similarity 0.6738 | rerank 0.658403217792511 | FAISS rank 1
3. 00-overview.md | Обзор mcp-ai > Подсистемы > Чат и сессии | similarity 0.6320 | rerank -0.31710463762283325 | FAISS rank 2
4. 05-llm-integration.md | Интеграция с LLM > Token usage и finish reason | similarity 0.5341 | rerank -0.5255876183509827 | FAISS rank 6
5. 23-use-cases.md | Пользовательские сценарии > Чат с LLM > Результат | similarity 0.5355 | rerank -0.5768247246742249 | FAISS rank 5

### q06

Original query: Чем отличаются get_current_weather и run_weather_collection_now с точки зрения persistence?

Rewritten query: Чем отличаются функции get_current_weather и run_weather_collection_now с точки зрения сохранения данных (persistence): запись в базу данных, кэширование, сохранение состояния, побочные эффекты и влияние на хранилище

Expected sources: 07-mcp-tools.md

Baseline retrieval:
1. 23-use-cases.md | Пользовательские сценарии > Weather summary > Components and tools | score 0.6403
2. 23-use-cases.md | Пользовательские сценарии > Forecast or hourly weather > Компоненты и tools | score 0.6107
3. 07-mcp-tools.md | Каталог MCP tools > Источник tools > `run_weather_collection_now` | score 0.6026
4. 10-orchestration.md | Orchestration и multi-tool flows > Реальные multi-tool сценарии > Создание наблюдения и сводка | score 0.5693
5. 09-scheduler-mcp.md | Scheduler MCP > Хранение задач и результатов > `weather_schedules` | score 0.5602

Enhanced retrieval:
1. 07-mcp-tools.md | Каталог MCP tools > Источник tools > `run_weather_collection_now` | similarity 0.5564 | rerank 2.124023675918579 | FAISS rank 8
2. 23-use-cases.md | Пользовательские сценарии > Forecast or hourly weather > Компоненты и tools | similarity 0.5260 | rerank 2.0871493816375732 | FAISS rank 13
3. 23-use-cases.md | Пользовательские сценарии > Weather request > Компоненты и tools | similarity 0.5179 | rerank 1.809622049331665 | FAISS rank 15
4. 23-use-cases.md | Пользовательские сценарии > Weather summary > Components and tools | similarity 0.6115 | rerank 1.7118327617645264 | FAISS rank 1
5. 10-orchestration.md | Orchestration и multi-tool flows > Реальные multi-tool сценарии > Создание наблюдения и сводка | similarity 0.5879 | rerank 1.4866055250167847 | FAISS rank 3

### q07

Original query: Какие настройки нужны старому OpenAI-compatible LLM client и как backend обрабатывает отсутствие конфигурации?

Rewritten query: Настройки конфигурации для устаревшего OpenAI-compatible LLM client: какие параметры требуются, какие значения по умолчанию и как backend обрабатывает отсутствие или неполноту конфигурации LLM client

Expected sources: 05-llm-integration.md, 16-configuration.md

Baseline retrieval:
1. 05-llm-integration.md | Интеграция с LLM > Клиент | score 0.7732
2. 21-known-limitations.md | Известные ограничения > Known limitations | score 0.7121
3. 01-architecture.md | Архитектура > LLM boundary | score 0.6888
4. 24-glossary.md | Глоссарий > Provider | score 0.6337
5. 17-running-project.md | Запуск проекта > Требования | score 0.6172

Enhanced retrieval:
1. 03-backend.md | Backend FastAPI > Dependencies > `get_llm_client()` | similarity 0.6465 | rerank 3.012761354446411 | FAISS rank 6
2. 21-known-limitations.md | Известные ограничения > Known limitations | similarity 0.7121 | rerank 1.8387556076049805 | FAISS rank 3
3. 01-architecture.md | Архитектура > LLM boundary | similarity 0.7147 | rerank 1.3324466943740845 | FAISS rank 2
4. 05-llm-integration.md | Интеграция с LLM > Обязательная конфигурация | similarity 0.6277 | rerank 1.2610418796539307 | FAISS rank 7
5. 05-llm-integration.md | Интеграция с LLM > Клиент | similarity 0.7524 | rerank 0.9728675484657288 | FAISS rank 1

### q08

Original query: Опишите полный путь MCP weather tool call: от выбора LLM до нормализованного результата, включая обработку ответа wttr.in.

Rewritten query: Полный путь вызова MCP weather tool: от выбора LLM и инициирования tool call до нормализованного результата, включая обработку ответа от wttr.in и преобразование данных погоды.

Expected sources: 22-data-flows.md, 06-mcp-architecture.md, 08-weather-mcp.md

Baseline retrieval:
1. 18-testing.md | Тестирование > Manual test scenarios > Проверка нескольких MCP tools | score 0.7909
2. 08-weather-mcp.md | Weather MCP | score 0.7750
3. 16-configuration.md | Конфигурация > Weather MCP | score 0.7616
4. 00-overview.md | Обзор mcp-ai > Поддерживаемые пользовательские сценарии | score 0.7524
5. 18-testing.md | Тестирование > Manual test scenarios > Проверка Weather MCP | score 0.7479

Enhanced retrieval:
1. 08-weather-mcp.md | Weather MCP > Flow погодного запроса | similarity 0.7556 | rerank 5.704260349273682 | FAISS rank 7
2. 22-data-flows.md | Потоки данных > Weather request | similarity 0.7430 | rerank 5.518996715545654 | FAISS rank 8
3. 18-testing.md | Тестирование > Manual test scenarios > Проверка Weather MCP | similarity 0.7703 | rerank 2.9538681507110596 | FAISS rank 4
4. 18-testing.md | Тестирование > Manual test scenarios > Проверка нескольких MCP tools | similarity 0.7886 | rerank 1.6433265209197998 | FAISS rank 3
5. 00-overview.md | Обзор mcp-ai > Поддерживаемые пользовательские сценарии | similarity 0.7602 | rerank 0.9546270966529846 | FAISS rank 6

### q09

Original query: Сравните хранение chat history и weather schedules: какие базы используются, кто управляет schema и какие данные в них хранятся?

Rewritten query: Сравнение хранения chat history и weather schedules: какие базы данных или хранилища используются для chat history и weather schedules, кто отвечает за управление схемой данных (schema ownership/management), какие данные хранятся в chat history и weather schedules, различия в моделях данных, схемах, владельцах схемы и типах сохраняемых данных.

Expected sources: 11-database.md, 01-architecture.md, 09-scheduler-mcp.md

Baseline retrieval:
1. 00-overview.md | Обзор mcp-ai > Поддерживаемые пользовательские сценарии | score 0.6320
2. 24-glossary.md | Глоссарий > Scheduler | score 0.5975
3. 23-use-cases.md | Пользовательские сценарии > Scheduled weather monitoring > Components and tools | score 0.5963
4. 23-use-cases.md | Пользовательские сценарии > Scheduled weather monitoring | score 0.5882
5. 00-overview.md | Обзор mcp-ai > Основные технологии > Хранилища | score 0.5842

Enhanced retrieval:
1. 00-overview.md | Обзор mcp-ai > Основные технологии > Хранилища | similarity 0.5119 | rerank 6.486069679260254 | FAISS rank 4
2. 02-project-structure.md | Структура проекта > `weather-mcp/` > `weather_mcp/scheduler.py` и `persistence.py` | similarity 0.4792 | rerank 5.253568649291992 | FAISS rank 13
3. 00-overview.md | Обзор mcp-ai > Подсистемы > Чат и сессии | similarity 0.5062 | rerank 5.233736991882324 | FAISS rank 5
4. 23-use-cases.md | Пользовательские сценарии > Scheduled weather monitoring | similarity 0.4998 | rerank 4.885075569152832 | FAISS rank 8
5. 00-overview.md | Обзор mcp-ai > Поддерживаемые пользовательские сценарии | similarity 0.5479 | rerank 4.277299404144287 | FAISS rank 1

### q10

Original query: Какие security-риски связаны с LLM ключом, MCP tools и отсутствием authentication в текущем проекте?

Rewritten query: Какие риски безопасности связаны с использованием ключа LLM API, инструментами MCP (Model Context Protocol) и отсутствием аутентификации в текущем проекте?

Expected sources: 20-security.md, 06-mcp-architecture.md

Baseline retrieval:
1. 00-overview.md | Обзор mcp-ai > Текущее состояние | score 0.7043
2. 20-security.md | Безопасность > Authentication и authorization | score 0.5835
3. 21-known-limitations.md | Известные ограничения > Known limitations | score 0.5824
4. 21-known-limitations.md | Известные ограничения > Not implemented | score 0.5803
5. 07-mcp-tools.md | Каталог MCP tools | score 0.5772

Enhanced retrieval:
1. 00-overview.md | Обзор mcp-ai > Текущее состояние | similarity 0.6181 | rerank -1.9600560665130615 | FAISS rank 1
2. 20-security.md | Безопасность > Риски MCP tool execution | similarity 0.5490 | rerank -3.37553071975708 | FAISS rank 6
3. 21-known-limitations.md | Известные ограничения > Not implemented | similarity 0.5375 | rerank -4.159687519073486 | FAISS rank 8
4. README.md | mcp-ai Knowledge Base > Documents | similarity 0.5077 | rerank -4.183060169219971 | FAISS rank 12
5. 18-testing.md | Тестирование > Coverage limits | similarity 0.5609 | rerank -4.40059757232666 | FAISS rank 4

### q11

Original query: А weather как прогноз получает?

Rewritten query: Как приложение/сервис weather получает данные прогноза погоды: источники данных, API, запросы к серверу, обновление прогноза.

Expected sources: 08-weather-mcp.md, 07-mcp-tools.md

Baseline retrieval:
1. 23-use-cases.md | Пользовательские сценарии > Forecast or hourly weather | score 0.7529
2. 23-use-cases.md | Пользовательские сценарии > Weather summary | score 0.7002
3. 23-use-cases.md | Пользовательские сценарии > Scheduled weather monitoring | score 0.6223
4. 23-use-cases.md | Пользовательские сценарии > Weather request | score 0.6141
5. 23-use-cases.md | Пользовательские сценарии > Forecast or hourly weather > Пример запроса | score 0.6085

Enhanced retrieval:
1. 08-weather-mcp.md | Weather MCP > Flow погодного запроса | similarity 0.6578 | rerank 1.3830701112747192 | FAISS rank 2
2. 22-data-flows.md | Потоки данных > Scheduler request | similarity 0.5795 | rerank 0.9549771547317505 | FAISS rank 13
3. 00-overview.md | Обзор mcp-ai > Подсистемы > Weather MCP | similarity 0.5978 | rerank 0.10993371903896332 | FAISS rank 10
4. 00-overview.md | Обзор mcp-ai > Поддерживаемые пользовательские сценарии | similarity 0.5766 | rerank -0.2341577708721161 | FAISS rank 14
5. 22-data-flows.md | Потоки данных > Weather request | similarity 0.6757 | rerank -0.71950364112854 | FAISS rank 1

### q12

Original query: После рестарта что будет с запланированными погодными штуками?

Rewritten query: Что происходит с запланированными задачами погодных эффектов или погодными событиями после перезапуска сервера или приложения?

Expected sources: 09-scheduler-mcp.md

Baseline retrieval:
1. 23-use-cases.md | Пользовательские сценарии > Forecast or hourly weather | score 0.6101
2. 23-use-cases.md | Пользовательские сценарии > Scheduled weather monitoring | score 0.5931
3. 23-use-cases.md | Пользовательские сценарии > Weather summary | score 0.5582
4. 23-use-cases.md | Пользовательские сценарии > Forecast or hourly weather > Пример запроса | score 0.5130
5. 23-use-cases.md | Пользовательские сценарии > Weather request | score 0.5129

Enhanced retrieval:
1. 09-scheduler-mcp.md | Scheduler MCP > Восстановление после restart | similarity 0.4973 | rerank -1.5984480381011963 | FAISS rank 9
2. 02-project-structure.md | Структура проекта > `weather-mcp/` > `weather-mcp/tests/` | similarity 0.5175 | rerank -4.236205577850342 | FAISS rank 6
3. 22-data-flows.md | Потоки данных > Application startup | similarity 0.5934 | rerank -4.9366936683654785 | FAISS rank 1
4. 23-use-cases.md | Пользовательские сценарии > Scheduled weather monitoring | similarity 0.5317 | rerank -5.093745231628418 | FAISS rank 3
5. 08-weather-mcp.md | Weather MCP > Назначение | similarity 0.4865 | rerank -5.715096473693848 | FAISS rank 15

### q13

Original query: Где лежит история диалогов, а где результаты погоды?

Rewritten query: Где хранится история диалогов и где хранятся результаты погоды?

Expected sources: 11-database.md, 09-scheduler-mcp.md

Baseline retrieval:
1. 12-memory-and-history.md | Память и история диалога | score 0.7112
2. 23-use-cases.md | Пользовательские сценарии > Conversation continuation | score 0.4580
3. 12-memory-and-history.md | Память и история диалога > Conversation history | score 0.4520
4. 24-glossary.md | Глоссарий > Session | score 0.4190
5. 23-use-cases.md | Пользовательские сценарии > Weather request > Пример запроса | score 0.3969

Enhanced retrieval:
1. 12-memory-and-history.md | Память и история диалога > Conversation history | similarity 0.4764 | rerank -1.3213189840316772 | FAISS rank 2
2. 12-memory-and-history.md | Память и история диалога > Долговременная память | similarity 0.4421 | rerank -3.009450674057007 | FAISS rank 5
3. 00-overview.md | Обзор mcp-ai > Поддерживаемые пользовательские сценарии | similarity 0.4333 | rerank -3.7549996376037598 | FAISS rank 6
4. 12-memory-and-history.md | Память и история диалога | similarity 0.7104 | rerank -5.806366443634033 | FAISS rank 1
5. 23-use-cases.md | Пользовательские сценарии > Conversation continuation | similarity 0.4712 | rerank -7.2054972648620605 | FAISS rank 3

## Observations

Metrics are generated from document-level expected sources. Enhanced is not declared superior by configuration: inspect the measured metrics and per-question ordering above. The threshold is a score cutoff for this normalized embedding/index pipeline, not a probability.
