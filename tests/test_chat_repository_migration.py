import sqlite3

from app.rag.chat_repository import ChatRepository


def test_day22_schema_is_migrated_without_removing_existing_chat(tmp_path):
    database = tmp_path / "rag.db"
    with sqlite3.connect(database) as connection:
        connection.executescript("""
            CREATE TABLE chats (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, created_at TEXT, updated_at TEXT);
            CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, mode TEXT, model TEXT, created_at TEXT, prompt_tokens INTEGER, completion_tokens INTEGER, total_tokens INTEGER);
            CREATE TABLE message_sources (id INTEGER PRIMARY KEY AUTOINCREMENT, message_id INTEGER NOT NULL, rank INTEGER NOT NULL, chunk_id TEXT NOT NULL, score REAL NOT NULL, file TEXT NOT NULL, section TEXT NOT NULL, section_path TEXT NOT NULL, text TEXT NOT NULL);
            INSERT INTO chats (id, title) VALUES (1, 'Day 22 chat');
            INSERT INTO messages (chat_id, role, content) VALUES (1, 'user', 'old question');
        """)

    repository = ChatRepository(database)
    chat = repository.get_chat(1)

    assert chat["title"] == "Day 22 chat"
    assert chat["messages"][0]["content"] == "old question"
    with sqlite3.connect(database) as connection:
        message_columns = {row[1] for row in connection.execute("PRAGMA table_info(messages)")}
        source_columns = {row[1] for row in connection.execute("PRAGMA table_info(message_sources)")}
        quote_table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'message_quotes'"
        ).fetchone()
    assert {"retrieval_mode", "original_question", "rewritten_query", "retrieval_metadata", "status"} <= message_columns
    assert {"source", "similarity_score", "rerank_score", "original_rank", "final_rank", "passed_threshold"} <= source_columns
    assert quote_table is not None
    assert chat["messages"][0]["quotes"] == []
    assert chat["task_state"] == {
        "goal": None,
        "clarifications": [],
        "constraints": [],
        "terms": {},
        "decisions": [],
        "open_questions": [],
    }
