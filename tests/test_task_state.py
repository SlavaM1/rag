import asyncio
import sqlite3

from app.rag.chat_repository import ChatRepository
from app.rag.llm import LLMResponse
from app.rag.task_state import ConversationalQueryBuilder, TaskState, TaskStateUpdater


class Provider:
    def __init__(self, content):
        self.content = content

    async def generate(self, messages, model, json_mode=False):
        return LLMResponse(self.content, model)


def test_task_state_updater_validates_structured_update():
    old = TaskState(goal="Понять Weather MCP")
    provider = Provider(
        '{"goal":"Понять scheduler flow","clarifications":[],"constraints":["только scheduler"],'
        '"terms":{"scheduler":"APScheduler"},"decisions":[],"open_questions":[]}'
    )

    update = asyncio.run(TaskStateUpdater(provider, "deepseek-flash").update(
        old, "Теперь рассматриваем только scheduler.", []
    ))

    assert update.updated
    assert update.state.goal == "Понять scheduler flow"
    assert update.state.constraints == ["только scheduler"]


def test_task_state_update_failure_keeps_previous_state():
    old = TaskState(goal="Понять Weather MCP")

    update = asyncio.run(TaskStateUpdater(Provider("not json"), "deepseek-flash").update(old, "Продолжим", []))

    assert not update.updated
    assert update.state == old


def test_task_state_persistence_and_chat_isolation(tmp_path):
    repository = ChatRepository(tmp_path / "rag.db")
    chat_a = int(repository.create_chat("A")["id"])
    chat_b = int(repository.create_chat("B")["id"])
    user_message_id = repository.add_user_message(chat_a, "Только backend")
    state = TaskState(goal="Понять backend", constraints=["не рассматривать frontend"])
    repository.add_assistant_message(
        chat_a, "Принято", "without_rag", "deepseek-flash",
        {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}, [],
        task_state=state, updated_from_message_id=user_message_id,
    )

    reloaded = ChatRepository(repository.database_path)
    assert reloaded.get_task_state(chat_a)[0] == state
    assert reloaded.get_task_state(chat_b)[0] == TaskState()

    reloaded.delete_chat(chat_a)
    with sqlite3.connect(repository.database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM chat_task_state WHERE chat_id = ?", (chat_a,)
        ).fetchone()[0] == 0


def test_conversational_query_builder_uses_state_and_recent_history():
    query = ConversationalQueryBuilder().build(
        "А где он хранится?",
        TaskState(goal="scheduler storage", terms={"он": "Weather MCP"}),
        [{"role": "assistant", "content": "Речь о periodic flow"}],
    )

    assert "scheduler storage" in query
    assert "он = Weather MCP" in query
    assert "Речь о periodic flow" in query
    assert query.endswith("А где он хранится?")
