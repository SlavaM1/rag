# Local RAG Search

Учебный локальный RAG retrieval project. Он индексирует **только** подготовленную Markdown-базу `docs/rag/**/*.md` и показывает похожие фрагменты документации. LLM, генерация ответов, чат и внешние API не используются.

## Architecture

```text
Markdown documents
       ↓
Markdown loader
       ↓
Fixed / Structural chunking
       ↓
Multilingual embeddings
       ↓
FAISS cosine similarity
       ↓
FastAPI Search API
       ↓
Vanilla JavaScript Web UI
```

`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` создаёт локальные multilingual embeddings для русского текста, английских терминов и кода. FAISS использует normalized vectors и inner product, то есть cosine similarity.

## Chunking

- **Fixed Size**: окна по 1000 символов с overlap 150, с попыткой сохранить границы слов.
- **Fixed Without Overlap**: окна по 1000 символов с сохранением границ слов, без повторения текста между чанками.
- **Structural Markdown**: Markdown-aware parser извлекает YAML front matter, H1, hierarchy headings и fenced code blocks. Каждый логический раздел остаётся отдельным; длинные разделы дополнительно делятся с overlap.

У каждого результата есть детерминированный `chunk_id`, путь документа, файл, title, section и section path.

## Run With Docker

```bash
docker compose up --build
```

Откройте http://localhost:8000. При первом старте контейнер скачает embedding model и построит отсутствующие индексы. Индексы находятся в host-каталоге `data/` благодаря volume и не пересоздаются при следующем рестарте.

Проверка состояния: `curl http://localhost:8000/health`

## Build Or Rebuild Indexes

Локально:

```bash
python -m app.rag.indexer
```

В Docker:

```bash
docker compose run --rm app python -m app.rag.indexer
```

Команда пересоздаёт все индексы идемпотентно: `data/rag/fixed/`, `data/rag/fixed_no_overlap/` и `data/rag/structural/`. Generated FAISS files намеренно не коммитятся, так как воспроизводятся из `docs/rag`.

## CLI Search

```bash
python -m app.rag.search_cli --query "Как работает Weather MCP?" --strategy structural --top-k 5
```

## API

`GET /health` возвращает `{"status":"ok"}`.

`POST /api/search`:

```json
{"query":"Как работает Weather MCP?","strategy":"structural","top_k":5}
```

`strategy` принимает `fixed`, `fixed_no_overlap` или `structural`; `top_k` ограничен 1-20, query не может быть пустым и длиннее 1000 символов.

## Compare Chunking

Evaluation dataset содержит 15 вопросов по реальным документам: FastAPI, Angular, LLM, MCP и Weather tools, scheduler, PostgreSQL/SQLite/Alembic, Docker, configuration, security и data flows.

```bash
python scripts/compare_chunking.py
```

Команда запускает обе стратегии, считает document-level Hit@1, Hit@3 и Hit@5 и записывает фактический отчёт в `data/rag/comparison.md`.

## Tests

```bash
pytest
```

Тесты используют fake embeddings, поэтому unit tests не скачивают модель.
