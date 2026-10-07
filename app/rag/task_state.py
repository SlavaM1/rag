from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .llm import LLMProvider


logger = logging.getLogger(__name__)


class TaskState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str | None = Field(default=None, max_length=500)
    clarifications: list[str] = Field(default_factory=list, max_length=20)
    constraints: list[str] = Field(default_factory=list, max_length=20)
    terms: dict[str, str] = Field(default_factory=dict)
    decisions: list[str] = Field(default_factory=list, max_length=20)
    open_questions: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("goal")
    @classmethod
    def normalize_goal(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("clarifications", "constraints", "decisions", "open_questions")
    @classmethod
    def normalize_items(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            item = value.strip()
            if item and item not in normalized:
                normalized.append(item[:500])
        return normalized

    @field_validator("terms")
    @classmethod
    def normalize_terms(cls, values: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for key, value in values.items():
            clean_key, clean_value = key.strip(), value.strip()
            if clean_key and clean_value:
                normalized[clean_key[:200]] = clean_value[:500]
        if len(normalized) > 30:
            raise ValueError("terms must contain at most 30 entries")
        return normalized


@dataclass(frozen=True)
class TaskStateUpdate:
    state: TaskState
    updated: bool


TASK_STATE_UPDATE_PROMPT = """Ты обновляешь компактную структурированную память задачи внутри одного чата.
Тебе даны текущая память, недавний разговор и новое сообщение пользователя.

Правила:
- обновляй только информацию, которая явно следует из нового сообщения или контекста разговора;
- не придумывай цели, ограничения, термины, решения или вопросы;
- сохраняй предыдущую информацию, если пользователь её не отменил;
- если пользователь явно сменил цель или условие, замени устаревшее значение;
- constraints содержит требования и исключения пользователя, включая «только backend» и «не рассматривать frontend»;
- clarifications содержит уточнения смысла, а не ограничения;
- terms сохраняет точное пользовательское обозначение как key и его каноническое значение как value;
- не превращай память в пересказ разговора и не сохраняй туда технические ответы ассистента;
- утверждение пользователя о проекте является пользовательским контекстом, а не доказанным техническим фактом;
- если сообщение не меняет память, верни её без изменений.

Верни только JSON без Markdown со всеми полями:
{"goal":null,"clarifications":[],"constraints":[],"terms":{},"decisions":[],"open_questions":[]}"""


class TaskStateUpdater:
    def __init__(self, provider: LLMProvider | None, model: str) -> None:
        self.provider = provider
        self.model = model

    async def update(
        self,
        current: TaskState,
        user_message: str,
        recent_history: list[dict[str, str]],
        provider: LLMProvider | None = None,
        model: str | None = None,
    ) -> TaskStateUpdate:
        payload = {
            "current_task_state": current.model_dump(mode="json"),
            "recent_conversation": recent_history,
            "new_user_message": user_message,
        }
        try:
            selected_provider = provider or self.provider
            if selected_provider is None:
                raise RuntimeError("No LLM provider configured")
            response = await selected_provider.generate(
                [
                    {"role": "system", "content": TASK_STATE_UPDATE_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                model or self.model,
                json_mode=True,
            )
            updated = TaskState.model_validate_json(_strip_json_fence(response.content))
            return TaskStateUpdate(updated, updated != current)
        except Exception:  # Memory enrichment must never make the answer flow unavailable.
            logger.warning("Task state update failed; keeping previous state", exc_info=True)
            return TaskStateUpdate(current, False)


class ConversationalQueryBuilder:
    def build(
        self,
        question: str,
        task_state: TaskState,
        recent_history: list[dict[str, str]],
    ) -> str:
        history = "\n".join(
            f"{message['role'].capitalize()}: {message['content']}" for message in recent_history
        ) or "(empty)"
        return (
            "TASK STATE (user goals and terminology, not a source of project facts)\n"
            f"{format_task_state(task_state)}\n\n"
            "RECENT CONVERSATION\n"
            f"{history}\n\n"
            "CURRENT QUESTION\n"
            f"{question}"
        )


def format_task_state(state: TaskState) -> str:
    terms = "\n".join(f"- {key} = {value}" for key, value in state.terms.items()) or "- none"
    return "\n".join(
        [
            f"Goal: {state.goal or 'none'}",
            f"Clarifications:\n{_format_items(state.clarifications)}",
            f"Constraints:\n{_format_items(state.constraints)}",
            f"Terms:\n{terms}",
            f"Decisions:\n{_format_items(state.decisions)}",
            f"Open questions:\n{_format_items(state.open_questions)}",
        ]
    )


def _format_items(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) or "- none"


def _strip_json_fence(content: str) -> str:
    value = content.strip()
    if value.startswith("```") and value.endswith("```"):
        lines = value.splitlines()
        if len(lines) >= 3:
            value = "\n".join(lines[1:-1]).strip()
    return value
