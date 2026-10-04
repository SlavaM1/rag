import asyncio

from app.rag.llm import LLMResponse
from app.rag.query_rewriter import QueryRewriter


class Provider:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    async def generate(self, messages, model, json_mode=False):
        self.calls.append((messages, model))
        if self.error:
            raise self.error
        return LLMResponse(self.response, model)


def test_query_rewriter_returns_successful_rewrite():
    assert asyncio.run(QueryRewriter(Provider("Weather MCP API forecast"), "deepseek-flash").rewrite("weather?")) == "Weather MCP API forecast"


def test_query_rewriter_uses_original_question_for_empty_result():
    assert asyncio.run(QueryRewriter(Provider("   "), "deepseek-flash").rewrite("weather?")) == "weather?"


def test_query_rewriter_uses_original_question_after_provider_failure():
    assert asyncio.run(QueryRewriter(Provider(error=RuntimeError("offline")), "deepseek-flash").rewrite("weather?")) == "weather?"


def test_query_rewriter_receives_conversational_context():
    provider = Provider("Где APScheduler хранит weather samples?")

    result = asyncio.run(QueryRewriter(provider, "deepseek-flash").rewrite(
        "А где он хранится?", "Goal: scheduler storage\nTerms: scheduler = APScheduler"
    ))

    assert result == "Где APScheduler хранит weather samples?"
    assert "scheduler = APScheduler" in provider.calls[0][0][1]["content"]
