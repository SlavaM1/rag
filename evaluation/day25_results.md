# Day 25 Long Conversation Evaluation

Deterministic checks only: persisted task-state fields, retrieval metadata, source/quote presence, and exact quote substrings. Answer semantics remain a manual review item.

## Scenario 1: Weather MCP, scheduler and storage

- Chat ID: 26
- Messages: 12
- Goal preserved: yes
- Constraints preserved: yes
- Terms preserved: yes
- Per-turn state expectations: 6/12
- Retrieval performed: 12/12
- API/provider errors: 6/12
- Answered: 6/12
- Answers with sources: 6/6
- Answers with quotes: 6/6
- Answers with valid quotes: 6/6
- Distinct final source sets: 6
- Messages and task state persisted: yes
- Final Task State:

```json
{
  "goal": "Понять flow scheduler → weather → storage",
  "clarifications": [],
  "constraints": [
    "Frontend не рассматриваем",
    "Интересует только backend"
  ],
  "terms": {
    "Weather MCP": "Weather MCP",
    "погодник": "Weather MCP",
    "шедулер": "APScheduler periodic job"
  },
  "decisions": [],
  "open_questions": [
    "Как шедулер регистрируется?",
    "Когда шедулер срабатывает, какой метод получает данные погоды?",
    "Где погодник сохраняет полученный им результат периодического запуска?",
    "Как называется таблица с этими samples и какие поля она хранит?",
    "Какое решение по persistence принято: SQLite или PostgreSQL, и где лежит файл?",
    "Что происходит с активными задачами после restart и воспроизводятся ли пропущенные запуски?"
  ]
}
```

## Scenario 2: FastAPI, Angular and API data flow

- Chat ID: 27
- Messages: 12
- Goal preserved: yes
- Constraints preserved: yes
- Terms preserved: yes
- Per-turn state expectations: 11/12
- Retrieval performed: 12/12
- API/provider errors: 1/12
- Answered: 11/12
- Answers with sources: 11/11
- Answers with quotes: 11/11
- Answers with valid quotes: 11/11
- Distinct final source sets: 10
- Messages and task state persisted: yes
- Final Task State:

```json
{
  "goal": "Понять backend persistence после финального ответа",
  "clarifications": [],
  "constraints": [
    "Пока рассматриваем только backend-обработку, без деталей CSS и UI"
  ],
  "terms": {
    "Angular": "Angular",
    "LLM": "LLM",
    "клиент": "Angular App",
    "бэк": "FastAPI backend"
  },
  "decisions": [],
  "open_questions": [
    "Что именно сохраняется после финального ответа?",
    "Какая база хранит chat history и кто управляет её schema?",
    "Сохраняются ли user и assistant сообщения одной операцией?",
    "Как меняется title?"
  ]
}
```
