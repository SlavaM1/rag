---
title: Глоссарий
project: mcp-ai
document_type: technical_documentation
source: repository
---

# Глоссарий

## LLM

Large Language Model. В `mcp-ai` LLM вызывается `OpenAICompatibleClient` для generation final answer и function calling.

## Provider

Внешний API, совместимый с OpenAI chat completions. Backend выбирает provider URL переменной `LLM_BASE_URL`; отдельные provider classes отсутствуют.

## Model

Строка `LLM_MODEL`, передаваемая как `model` в `/chat/completions`. `.env.example` приводит `deepseek-chat` как пример.

## MCP

Model Context Protocol. В `mcp-ai` backend использует MCP 2.2 Streamable HTTP для tool discovery/execution.

## MCP server

Процесс, публикующий MCP tools. Bundled `weather-mcp` доступен на `/mcp`.

## MCP client

`MCPToolsClient` backend, открывающий `ClientSession`, выполняющий `initialize`, `list_tools` и `call_tool`.

## MCP tool

Функция MCP server с именем, description и JSON input schema. В текущем project восемь weather tools.

## Tool call

Запрос LLM вызвать function с JSON arguments. `ChatAgent` проверяет tool name и выполняет MCP call, сохраняя result/error/duration.

## Orchestration

Логика `ChatAgent.run(...)`, соединяющая history, LLM response и последовательные MCP calls до final text.

## Session

`ChatSession` PostgreSQL record, объединяющий messages одной беседы.

## Message

`ChatMessage` PostgreSQL record с role/content и optional `mcp_data` JSONB.

## Scheduler

`WeatherScheduler` на APScheduler внутри weather-mcp. Создаёт interval jobs для сбора weather samples.

## Embedding

Векторное представление текста. Runtime `mcp-ai` embeddings не создаёт и не хранит.

## RAG

Retrieval-Augmented Generation. Runtime project RAG не реализует; `docs/rag/` подготовлен как потенциальный внешний corpus.

## JSONB

PostgreSQL binary JSON type. `ChatMessage.mcp_data` хранит technical MCP metadata.

## Migration

Изменение schema. Alembic migration создаёт PostgreSQL chat schema; `WeatherRepository` отдельно применяет additive SQLite changes.

## Healthcheck

Проверка доступности service. Compose использует `pg_isready` для PostgreSQL, HTTP `/health` для weather/backend/frontend; frontend health обслуживается nginx.
