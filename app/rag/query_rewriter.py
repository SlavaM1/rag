from __future__ import annotations

import logging

from .llm import LLMProvider


logger = logging.getLogger(__name__)

QUERY_REWRITE_PROMPT = """Ты преобразуешь пользовательский вопрос в поисковый запрос для semantic retrieval по технической документации.
Сохрани исходный смысл, раскрой неявные ссылки и технические формулировки, добавь полезные ключевые понятия.
Вход может содержать Task State и недавний разговор. Используй их только для разрешения ссылок, цели, ограничений и терминов.
Не отвечай на вопрос, не придумывай факты и верни только переписанный поисковый запрос.
Если вопрос уже хорошо сформулирован для поиска, верни его практически без изменений."""


class QueryRewriter:
    def __init__(self, provider: LLMProvider, model: str) -> None:
        self.provider = provider
        self.model = model

    async def rewrite(self, original_question: str, conversational_context: str | None = None) -> str:
        try:
            response = await self.provider.generate(
                [
                    {"role": "system", "content": QUERY_REWRITE_PROMPT},
                    {"role": "user", "content": conversational_context or original_question},
                ],
                self.model,
            )
            rewritten = response.content.strip()
            if rewritten:
                return rewritten
            logger.warning("Query rewrite returned an empty result; using original question")
        except Exception:  # The answer flow must remain available when this optional step fails.
            logger.warning("Query rewrite failed; using original question", exc_info=True)
        return original_question
