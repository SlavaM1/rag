# Local RAG Chat

Учебный проект, который явно показывает разницу между baseline generation и retrieval-augmented generation поверх Markdown-базы `docs/rag/**/*.md`. Day 21 retrieval сохраняется: Markdown loader, fixed/structural chunking, multilingual embeddings, FAISS, `/api/search`, CLI и chunking evaluation.

## Day 23 - Query Rewrite, Filtering And Reranking

Day 22 behaviour remains available as `baseline` retrieval:

```text
Question
  ↓
FAISS Top-K
  ↓
Context
  ↓
DeepSeek
```

The default `enhanced` retrieval pipeline is deliberately separate:

```text
Original question
  ↓
Query Rewrite
  ↓
FAISS candidate search (15)
  ↓
Similarity filter
  ↓
Local multilingual reranker
  ↓
Final Top-K (5)
  ↓
Context + original question
  ↓
DeepSeek
```

Query rewrite improves the search wording, not the answer question. For example, `А weather как прогноз получает?` can become `Как Weather MCP получает прогноз погоды и какие API или tools используются?`; the final model still receives the original user text.

FAISS always returns nearest chunks, including weak matches. `RAG_SIMILARITY_THRESHOLD` removes weak candidates before generation. The default `0.40` is the first tested cutoff that actually removes weak candidates in this corpus; its expected-source trade-off is recorded in the Day 23 report. It is not a percentage or confidence value. If every candidate is removed, the model receives an explicit no-relevant-context instruction and must not answer from its own knowledge.

Vector search is fast candidate selection. The CPU-compatible local cross-encoder `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` compares the rewritten query with each surviving chunk more precisely and reorders them. It is lazy-loaded once per application process; its raw score is also not a probability.

`/api/chat` exposes `baseline` and `enhanced`; internal environment flags allow rewrite, filter, and rerank stages to be disabled independently for experiments. The UI keeps only Baseline and Enhanced. Every enhanced response includes original FAISS rank, final rank, similarity score, rerank score, candidates that failed the threshold, timings, and the final context sources.

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
- WITH RAG / WITHOUT RAG and Baseline / Enhanced retrieval selector;
- friendly model selector DeepSeek Flash / DeepSeek V4 Pro;
- fixed / structural strategy, candidate Top-K and final Top-K;
- раскрываемые sources и RAG details с chunks и usage;
- Day 22 compare (RAG / without RAG) and Day 23 compare (Baseline / Enhanced), including retrieval metadata.

## API

`GET /health` возвращает service health.

`POST /api/search` сохраняет Day 21 retrieval API:

```json
{"query":"Как работает Weather MCP?","strategy":"structural","top_k":5}
```

`POST /api/chat` создаёт или продолжает persisted chat:

```json
{"chat_id":null,"question":"Как работает Weather MCP?","mode":"with_rag","retrieval_mode":"enhanced","model":"deepseek-flash","strategy":"structural","candidate_top_k":15,"final_top_k":5}
```

`POST /api/compare` запускает без persistence две ветки одного question с одной model:

```json
{"question":"Как работает Weather MCP?","model":"deepseek-flash","strategy":"structural","top_k":5}
```

`POST /api/compare-retrieval` compares the same question, model, strategy and final Top-K across baseline and enhanced RAG:

```json
{"question":"Как работает Weather MCP?","model":"deepseek-flash","strategy":"structural","candidate_top_k":15,"final_top_k":5}
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

Day 22 has ten documentation-grounded questions in `evaluation/day22_questions.json`. Day 23 retains them and adds conversational and multi-document retrieval cases in `evaluation/day23_questions.json`. Run `docker compose run --rm app python scripts/evaluate_day23.py` to write `data/rag/day23_comparison.md`; the committed run is in `evaluation/day23_results.md`. It reports Hit@1/3/5, candidate/filter/final averages, reranking changes, score distributions, original/rewritten query, and retrieved chunks. No LLM-as-a-judge is used.

## Tests

```bash
pytest
```

Tests use fake embeddings and `FakeLLMProvider`; they never call DeepSeek. They cover retrieval branching, context, model validation, compare fairness, SQLite persistence and primary FastAPI endpoints.
