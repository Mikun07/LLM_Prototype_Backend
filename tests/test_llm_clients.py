from __future__ import annotations

from app.config import Settings
from app.models import ModelName
from app.services.llm_clients import LlmClient, ProviderRequestError
from app.services.prompt_service import PromptMessages


class OpenAiQuotaError(Exception):
    """Fake OpenAI quota error used by retry tests."""

    status_code = 429
    body = {
        "error": {
            "message": "You exceeded your current quota.",
            "code": "insufficient_quota",
        },
    }


class AnthropicCreditError(Exception):
    """Fake Anthropic billing error used by retry tests."""

    status_code = 400
    body = {
        "error": {
            "message": (
                "Your credit balance is too low to access the Anthropic API. "
                "Please go to Plans & Billing to upgrade or purchase credits."
            ),
            "type": "invalid_request_error",
        },
    }


def settings_for_test() -> Settings:
    """Return a Settings object suitable for unit tests with real-LLM mode enabled."""
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
    """LLM client that always raises the fake OpenAI quota error."""

    def __init__(self) -> None:
        super().__init__(settings_for_test())
        self.calls = 0

    async def complete(self, model: ModelName, prompt: PromptMessages) -> str:
        """Always raise OpenAiQuotaError and count the attempt."""
        self.calls += 1
        raise OpenAiQuotaError()


class AnthropicCreditFailingClient(LlmClient):
    """LLM client that always raises the fake Anthropic billing error."""

    def __init__(self) -> None:
        super().__init__(settings_for_test())
        self.calls = 0

    async def complete(self, model: ModelName, prompt: PromptMessages) -> str:
        """Always raise AnthropicCreditError and count the attempt."""
        self.calls += 1
        raise AnthropicCreditError()


async def test_openai_insufficient_quota_is_not_retried() -> None:
    """Verify that an OpenAI quota error raises immediately without retrying."""
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
        assert str(error) == "ChatGPT billing issue. Add credits or use mock mode."
    else:
        raise AssertionError("Expected ProviderRequestError for exhausted OpenAI quota.")


async def test_anthropic_low_credit_error_is_short_and_not_retried() -> None:
    """Verify that an Anthropic billing error raises a short message without retrying."""
    client = AnthropicCreditFailingClient()

    try:
        await client.complete_with_retries(
            "claude",
            PromptMessages(system="system", user="user"),
        )
    except ProviderRequestError as error:
        assert client.calls == 1
        assert error.status_code == 400
        assert error.code == "billing_error"
        assert str(error) == "Claude billing issue. Add credits or use mock mode."
        assert "credit balance" not in str(error).lower()
        assert "plans & billing" not in str(error).lower()
    else:
        raise AssertionError("Expected ProviderRequestError for low Anthropic credits.")
