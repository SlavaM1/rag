from __future__ import annotations

import sqlite3
import json
from pathlib import Path


class ChatNotFoundError(ValueError):
    pass


class ChatRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    mode TEXT CHECK(mode IN ('with_rag', 'without_rag')),
                    model TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    status TEXT CHECK(status IN ('answered', 'insufficient_context'))
                );
                CREATE INDEX IF NOT EXISTS messages_chat_id_created_at ON messages(chat_id, id);
                CREATE TABLE IF NOT EXISTS message_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                    rank INTEGER NOT NULL,
                    chunk_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    source TEXT,
                    file TEXT NOT NULL,
                    section TEXT NOT NULL,
                    section_path TEXT NOT NULL,
                    text TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS message_sources_message_id_rank ON message_sources(message_id, rank);
                CREATE TABLE IF NOT EXISTS message_quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                    source_number INTEGER NOT NULL,
                    chunk_id TEXT NOT NULL,
                    quote TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS message_quotes_message_id_source
                    ON message_quotes(message_id, source_number, id);
                """
            )
            # ALTER TABLE is additive, so existing Day 22 databases and conversations remain intact.
            self._add_column(connection, "messages", "retrieval_mode TEXT")
            self._add_column(connection, "messages", "original_question TEXT")
            self._add_column(connection, "messages", "rewritten_query TEXT")
            self._add_column(connection, "messages", "retrieval_metadata TEXT")
            self._add_column(connection, "messages", "status TEXT")
            self._add_column(connection, "message_sources", "source TEXT")
            self._add_column(connection, "message_sources", "similarity_score REAL")
            self._add_column(connection, "message_sources", "rerank_score REAL")
            self._add_column(connection, "message_sources", "original_rank INTEGER")
            self._add_column(connection, "message_sources", "final_rank INTEGER")
            self._add_column(connection, "message_sources", "passed_threshold INTEGER")

    def create_chat(self, title: str = "New chat") -> dict[str, object]:
        with self._connect() as connection:
            cursor = connection.execute("INSERT INTO chats (title) VALUES (?)", (title,))
            return self._chat(connection, cursor.lastrowid)

    def list_chats(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM chats ORDER BY updated_at DESC, id DESC").fetchall()
            return [dict(row) for row in rows]

    def get_chat(self, chat_id: int) -> dict[str, object]:
        with self._connect() as connection:
            chat = self._chat(connection, chat_id)
            messages = connection.execute("SELECT * FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,)).fetchall()
            chat["messages"] = [self._message(connection, row) for row in messages]
            return chat

    def delete_chat(self, chat_id: int) -> None:
        with self._connect() as connection:
            if connection.execute("DELETE FROM chats WHERE id = ?", (chat_id,)).rowcount == 0:
                raise ChatNotFoundError(f"Chat {chat_id} was not found")

    def recent_messages(self, chat_id: int, limit: int) -> list[dict[str, str]]:
        with self._connect() as connection:
            self._chat(connection, chat_id)
            rows = connection.execute(
                "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT ?", (chat_id, limit)
            ).fetchall()
            return [dict(row) for row in reversed(rows)]

    def add_user_message(self, chat_id: int, content: str) -> int:
        with self._connect() as connection:
            chat = self._chat(connection, chat_id)
            if chat["title"] == "New chat":
                connection.execute("UPDATE chats SET title = ? WHERE id = ?", (self._title(content), chat_id))
            cursor = connection.execute(
                "INSERT INTO messages (chat_id, role, content) VALUES (?, 'user', ?)", (chat_id, content)
            )
            self._touch(connection, chat_id)
            return int(cursor.lastrowid)

    def add_assistant_message(
        self,
        chat_id: int,
        content: str,
        mode: str,
        model: str,
        usage: dict[str, int | None],
        sources: list[dict[str, object]],
        retrieval_mode: str | None = None,
        original_question: str | None = None,
        rewritten_query: str | None = None,
        retrieval: dict[str, object] | None = None,
        status: str = "answered",
        quotes: list[dict[str, object]] | None = None,
    ) -> int:
        with self._connect() as connection:
            self._chat(connection, chat_id)
            cursor = connection.execute(
                """INSERT INTO messages
                (chat_id, role, content, mode, model, prompt_tokens, completion_tokens, total_tokens,
                 retrieval_mode, original_question, rewritten_query, retrieval_metadata, status)
                VALUES (?, 'assistant', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    chat_id, content, mode, model, usage["prompt_tokens"], usage["completion_tokens"], usage["total_tokens"],
                    retrieval_mode, original_question, rewritten_query,
                    json.dumps(retrieval, ensure_ascii=False) if retrieval is not None else None,
                    status,
                ),
            )
            message_id = int(cursor.lastrowid)
            connection.executemany(
                """INSERT INTO message_sources
                (message_id, rank, chunk_id, score, source, file, section, section_path, text, similarity_score,
                  rerank_score, original_rank, final_rank, passed_threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        message_id,
                        source["number"],
                        source["chunk_id"],
                        source["score"],
                        source["source"],
                        source["file"],
                        source["section"],
                        source["section_path"],
                        source["text"],
                        source.get("similarity_score", source["score"]),
                        source.get("rerank_score"),
                        source.get("original_rank"),
                        source.get("final_rank"),
                        int(source["passed_threshold"]) if source.get("passed_threshold") is not None else None,
                    )
                    for source in sources
                ],
            )
            connection.executemany(
                """INSERT INTO message_quotes (message_id, source_number, chunk_id, quote)
                VALUES (?, ?, ?, ?)""",
                [
                    (message_id, quote["source_number"], quote["chunk_id"], quote["quote"])
                    for quote in quotes or []
                ],
            )
            self._touch(connection, chat_id)
            return message_id

    @staticmethod
    def _title(question: str) -> str:
        return question.strip().replace("\n", " ")[:80] or "New chat"

    @staticmethod
    def _touch(connection: sqlite3.Connection, chat_id: int) -> None:
        connection.execute("UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (chat_id,))

    @staticmethod
    def _add_column(connection: sqlite3.Connection, table: str, definition: str) -> None:
        name = definition.split()[0]
        columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
        if name not in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")

    @staticmethod
    def _chat(connection: sqlite3.Connection, chat_id: int) -> dict[str, object]:
        row = connection.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if row is None:
            raise ChatNotFoundError(f"Chat {chat_id} was not found")
        return dict(row)

    @staticmethod
    def _message(connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, object]:
        message = dict(row)
        sources = connection.execute(
            """SELECT rank, chunk_id, score, source, file, section, section_path, text, similarity_score, rerank_score,
               original_rank, final_rank, passed_threshold FROM message_sources WHERE message_id = ? ORDER BY rank""",
            (message["id"],),
        ).fetchall()
        message["sources"] = []
        for row_source in sources:
            source = dict(row_source)
            source["source"] = source["source"] or source["file"]
            if source["passed_threshold"] is not None:
                source["passed_threshold"] = bool(source["passed_threshold"])
            message["sources"].append({"number": source["rank"], **source})
        source_by_number = {source["number"]: source for source in message["sources"]}
        quote_rows = connection.execute(
            """SELECT source_number, chunk_id, quote FROM message_quotes
            WHERE message_id = ? ORDER BY source_number, id""",
            (message["id"],),
        ).fetchall()
        message["quotes"] = []
        for quote_row in quote_rows:
            quote = dict(quote_row)
            source = source_by_number.get(quote["source_number"], {})
            message["quotes"].append(
                {
                    **quote,
                    "source": source.get("source", ""),
                    "file": source.get("file", ""),
                    "section": source.get("section", ""),
                    "section_path": source.get("section_path", ""),
                }
            )
        message["usage"] = {
            "prompt_tokens": message.pop("prompt_tokens"),
            "completion_tokens": message.pop("completion_tokens"),
            "total_tokens": message.pop("total_tokens"),
        }
        retrieval_metadata = message.pop("retrieval_metadata", None)
        message["retrieval"] = json.loads(retrieval_metadata) if retrieval_metadata else None
        return message
