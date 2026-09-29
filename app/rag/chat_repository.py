from __future__ import annotations

import sqlite3
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
                    total_tokens INTEGER
                );
                CREATE INDEX IF NOT EXISTS messages_chat_id_created_at ON messages(chat_id, id);
                CREATE TABLE IF NOT EXISTS message_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                    rank INTEGER NOT NULL,
                    chunk_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    file TEXT NOT NULL,
                    section TEXT NOT NULL,
                    section_path TEXT NOT NULL,
                    text TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS message_sources_message_id_rank ON message_sources(message_id, rank);
                """
            )

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
    ) -> int:
        with self._connect() as connection:
            self._chat(connection, chat_id)
            cursor = connection.execute(
                """INSERT INTO messages
                (chat_id, role, content, mode, model, prompt_tokens, completion_tokens, total_tokens)
                VALUES (?, 'assistant', ?, ?, ?, ?, ?, ?)""",
                (chat_id, content, mode, model, usage["prompt_tokens"], usage["completion_tokens"], usage["total_tokens"]),
            )
            message_id = int(cursor.lastrowid)
            connection.executemany(
                """INSERT INTO message_sources
                (message_id, rank, chunk_id, score, file, section, section_path, text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        message_id,
                        source["number"],
                        source["chunk_id"],
                        source["score"],
                        source["file"],
                        source["section"],
                        source["section_path"],
                        source["text"],
                    )
                    for source in sources
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
    def _chat(connection: sqlite3.Connection, chat_id: int) -> dict[str, object]:
        row = connection.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if row is None:
            raise ChatNotFoundError(f"Chat {chat_id} was not found")
        return dict(row)

    @staticmethod
    def _message(connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, object]:
        message = dict(row)
        sources = connection.execute(
            "SELECT rank, chunk_id, score, file, section, section_path, text FROM message_sources WHERE message_id = ? ORDER BY rank",
            (message["id"],),
        ).fetchall()
        message["sources"] = [{"number": source["rank"], **dict(source)} for source in sources]
        message["usage"] = {
            "prompt_tokens": message.pop("prompt_tokens"),
            "completion_tokens": message.pop("completion_tokens"),
            "total_tokens": message.pop("total_tokens"),
        }
        return message
