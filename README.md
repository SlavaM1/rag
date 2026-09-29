# Local RAG Chat

Учебный проект, который явно показывает разницу между baseline generation и retrieval-augmented generation поверх Markdown-базы `docs/rag/**/*.md`. Day 21 retrieval сохраняется: Markdown loader, fixed/structural chunking, multilingual embeddings, FAISS, `/api/search`, CLI и chunking evaluation.

## Day 22 - RAG Generation

### WITHOUT RAG

```text
Question
   ↓
DeepSeek
   ↓
Answer
```

Baseline не вызывает embeddings, FAISS, retrieval или knowledge base.

### WITH RAG

```text
Question
   ↓
Embedding
   ↓
FAISS Top-K
   ↓
Context
   ↓
DeepSeek
   ↓
Answer + Sources
```

`RAGService` выполняет flow явно: `SearchService -> ContextBuilder -> DeepSeekProvider`. Фактические retrieved chunks сохраняются и возвращаются как sources; LLM не определяет их самостоятельно. По умолчанию используется `structural` и Top-K `5`.

## DeepSeek

Provider: DeepSeek, официальный OpenAI-compatible Chat Completions API.

- Base URL: `https://api.deepseek.com`
- Models: `deepseek-flash`, `deepseek-v4-pro`
- Default: `deepseek-flash`
- Generation defaults: temperature `0.2`, max output tokens `1024`, timeout `45` seconds, thinking disabled

Создайте `.env` из `.env.example` и заполните только ключ:

```text
DEEPSEEK_API_KEY=<your-key>
```

Все прочие DeepSeek значения уже имеют рабочие defaults. Frontend никогда не получает и не отправляет ключ или base URL. Backend допускает только две перечисленные модели. Для Compare оба запроса получают одинаковые model, temperature, max tokens и остальные generation parameters; различается только добавление retrieval context.

## Run With Docker

```bash
docker compose up --build -d
docker compose ps
```

Откройте http://localhost:8000. При первом запуске отсутствующие FAISS indexes строятся в mounted `data/`; `./data:/app/data` сохраняет indexes, metadata, Hugging Face embedding cache и SQLite chat history между рестартами.

Проверка: `curl http://localhost:8000/health`.

SQLite chat history находится в `data/rag.db`. Она содержит `chats`, `messages` и `message_sources`; история отправляет DeepSeek только последние `CHAT_HISTORY_MESSAGES=10` сообщений. Старые sources показываются из SQLite без нового retrieval.

## Web UI

Vanilla JavaScript UI поддерживает:

- новый чат и список сохранённых чатов;
- WITH RAG / WITHOUT RAG;
- friendly model selector DeepSeek Flash / DeepSeek V4 Pro;
- fixed / structural strategy и Top-K;
- раскрываемые sources и RAG details с chunks и usage;
- кнопку сравнения двух ответов от одной модели.

## API

`GET /health` возвращает service health.

`POST /api/search` сохраняет Day 21 retrieval API:

```json
{"query":"Как работает Weather MCP?","strategy":"structural","top_k":5}
```

`POST /api/chat` создаёт или продолжает persisted chat:

```json
{"chat_id":null,"question":"Как работает Weather MCP?","mode":"with_rag","model":"deepseek-flash","strategy":"structural","top_k":5}
```

`POST /api/compare` запускает без persistence две ветки одного question с одной model:

```json
{"question":"Как работает Weather MCP?","model":"deepseek-flash","strategy":"structural","top_k":5}
```

Chats API: `POST /api/chats`, `GET /api/chats`, `GET /api/chats/{chat_id}`, `DELETE /api/chats/{chat_id}`.

Provider errors mapped to safe API messages: configuration `503`, rate limit `429`, timeout `504`, authentication/unavailable model/network/malformed provider response `502`. Secret values are not returned or logged.

## Indexing And Search

Build/rebuild both indexes locally:

```bash
python -m app.rag.indexer
```

Or in Docker:

```bash
docker compose run --rm app python -m app.rag.indexer
```

CLI search remains available:

```bash
python -m app.rag.search_cli --query "Как работает Weather MCP?" --strategy structural --top-k 5
```

Fixed chunking uses 1000-character windows with 150 overlap. Structural chunking preserves Markdown hierarchy and only splits long sections. Embeddings use `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; normalized FAISS inner product represents cosine similarity.

## Evaluation

Day 21 retrieval/chunking comparison:

```bash
python scripts/compare_chunking.py
```

Day 22 has ten documentation-grounded questions in `evaluation/day22_questions.json`: three factual, four medium and three multi-document questions. Use Compare UI and record manual findings in `evaluation/day22_results.md`; no LLM-as-a-judge is used.

## Tests

```bash
pytest
```

Tests use fake embeddings and `FakeLLMProvider`; they never call DeepSeek. They cover retrieval branching, context, model validation, compare fairness, SQLite persistence and primary FastAPI endpoints.
