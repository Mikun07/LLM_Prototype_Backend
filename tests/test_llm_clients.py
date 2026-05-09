from __future__ import annotations

from app.config import Settings
from app.models import ModelName
from app.services.llm_clients import LlmClient, ProviderRequestError
from app.services.prompt_service import PromptMessages


class OpenAiQuotaError(Exception):
    status_code = 429
    body = {
        "error": {
            "message": "You exceeded your current quota.",
            "code": "insufficient_quota",
        },
    }


def settings_for_test() -> Settings:
    return Settings(
        use_real_llm=True,
        anthropic_api_key="anthropic-test",
        openai_api_key="openai-test",
        claude_model="claude-test",
        openai_model="openai-test",
        llm_temperature=0.1,
        llm_max_tokens=128,
        llm_max_retries=3,
        inconsistency_max_group_size=20,
        max_csv_size_mb=10,
        backend_host="127.0.0.1",
        backend_port=8000,
        cors_origins=["http://127.0.0.1:5173"],
        log_level="INFO",
        log_raw_llm_responses=False,
        log_dir="logs",
    )


class QuotaFailingClient(LlmClient):
    def __init__(self) -> None:
        super().__init__(settings_for_test())
        self.calls = 0

    async def complete(self, model: ModelName, prompt: PromptMessages) -> str:
        self.calls += 1
        raise OpenAiQuotaError()


async def test_openai_insufficient_quota_is_not_retried() -> None:
    client = QuotaFailingClient()

    try:
        await client.complete_with_retries(
            "chatgpt",
            PromptMessages(system="system", user="user"),
        )
    except ProviderRequestError as error:
        assert client.calls == 1
        assert error.status_code == 429
        assert error.code == "insufficient_quota"
        assert "OpenAI API quota is exhausted" in str(error)
    else:
        raise AssertionError("Expected ProviderRequestError for exhausted OpenAI quota.")
