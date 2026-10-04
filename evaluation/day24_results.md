# Day 24 Grounding Evaluation

Deterministic checks validate source presence, quote presence, source numbers, chunk IDs, and exact quote substrings. Semantic support remains a manual review item.

| # | Question | Answer | Sources present | Quotes present | Quotes valid | Meaning supported |
|---|---|---|---|---|---|---|
| 1 | Какой HTTP path и transport использует Weather MCP server? | Weather MCP server использует MCP 2.2 Streamable HTTP server [1] и публикует `/mcp` и `/health` [4]. | yes | yes | yes | yes (manual) |
| 2 | Какие ограничения имеет параметр days у get_weather_forecast? | Параметр `days` у `get_weather_forecast` является обязательным и принимает целое число от 1 до 3 [1]. | yes | yes | yes | yes (manual) |
| 3 | Где находятся FAISS индексы этого учебного RAG-проекта и когда они строятся? | В предоставленном CONTEXT нет информации о местоположении FAISS-индексов или о том, когда они строятся. Упоминается только, что код не создаёт embeddings, vector store или retri... | yes | yes | yes | yes, incomplete (manual) |
| 4 | Почему WeatherScheduler не воспроизводит пропущенные запуски после restart и как восстанавливаются active schedules? | После restart `WeatherScheduler.start()` читает `list_schedules(active_only=True)` и повторно регистрирует jobs [1]. Пропущенные запуски не воспроизводятся, потому что APSchedul... | yes | yes | yes | yes (manual) |
| 5 | Как проходит обычное сообщение пользователя от Angular UI до сохранения истории чата? | Обычное сообщение проходит по цепочке: User → Angular App → nginx /api/ → FastAPI POST /api/sessions/{session_id}/messages → ChatAgent → OpenAICompatibleClient → LLM → FastAPI и... | yes | yes | yes | yes (manual) |
| 6 | Чем отличаются get_current_weather и run_weather_collection_now с точки зрения persistence? | В предоставленном CONTEXT нет сведений о persistence для `get_current_weather`. Про `run_weather_collection_now` известно, что этот tool сохраняет один sample и не создаёт sched... | yes | yes | yes | yes, incomplete (manual) |
| 7 | Какие настройки нужны старому OpenAI-compatible LLM client и как backend обрабатывает отсутствие конфигурации? | Клиенту нужны непустые настройки `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` — их требует `ensure_configured()` [4]. Провайдер определяется через `LLM_BASE_URL`, а модель — через... | yes | yes | yes | yes (manual) |
| 8 | Опишите полный путь MCP weather tool call: от выбора LLM до нормализованного результата, включая обработку ответа wttr.in. | Полный путь MCP weather tool call выглядит так: LLM выбирает weather tool из discovery schema [2]. Затем `MCPToolsClient.call_tool(...)` передаёт name и JSON object arguments `/... | yes | yes | yes | yes (manual) |
| 9 | Сравните хранение chat history и weather schedules: какие базы используются, кто управляет schema и какие данные в них хранятся? | Chat history хранится в PostgreSQL 17, который хранит чат-сессии и сообщения [1]. Weather schedules и weather samples хранятся в локальном SQLite-файле `weather.db` внутри `weat... | yes | yes | yes | yes, incomplete (manual) |
| 10 | Какие security-риски связаны с LLM ключом, MCP tools и отсутствием authentication в текущем проекте? | В текущем проекте нет authentication, authorization и multi-user isolation [1]. Что касается MCP tools, backend разрешает вызов только names, discovered в current MCP session, ч... | yes | yes | yes | yes, incomplete (manual) |

## Metrics

- Questions tested: 10
- Answered RAG requests: 10
- Sources coverage: 10/10
- Quotes coverage: 10/10
- Quote validation: 31/31
- Semantic quote check: 10/10 manually supported

## Manual Notes

- q03 is grounded but does not answer the expected FAISS location/startup points because retrieval selected unrelated limitation chunks.
- q06 supports `run_weather_collection_now`, but the final context did not provide the expected `get_current_weather` persistence contrast.
- q09 supports the storage technologies and data, but omits part of the expected schema-ownership comparison.
- q10 supports authentication and MCP-tool risks, but omits the expected LLM-key handling risk.
