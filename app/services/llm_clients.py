from __future__ import annotations

import asyncio
import json
import re
from typing import cast

from app.config import Settings, get_settings
from app.models import ModelName
from app.services.prompt_service import PromptMessages

AMBIGUITY_SIGNALS = ("may", "should", "could", "fast", "easy", "quickly", "support")
INCONSISTENCY_SIGNALS = ("must not", "shall not", "never", "without authentication")


class ProviderRequestError(RuntimeError):
    """Normalised provider error with retry and status metadata."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        status_code: int | None = None,
        code: str | None = None,
        retryable: bool = True,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.code = code
        self.retryable = retryable


def provider_name(model: ModelName) -> str:
    """Return the provider organisation name for a given model."""
    return "OpenAI" if model == "chatgpt" else "Anthropic"


def user_model_name(model: ModelName) -> str:
    """Return the display name shown to users for a given model."""
    return "ChatGPT" if model == "chatgpt" else "Claude"


def extract_status_code(exc: Exception) -> int | None:
    """Extract an HTTP status code from a provider SDK exception, if present."""
    value = getattr(exc, "status_code", None)
    return value if isinstance(value, int) else None


def extract_error_body(exc: Exception) -> dict[str, object]:
    """Extract the response body dict from a provider SDK exception, if present."""
    body = getattr(exc, "body", None)
    return body if isinstance(body, dict) else {}


def extract_error_code(exc: Exception) -> str | None:
    """Extract a machine-readable error code from a provider SDK exception body."""
    body = extract_error_body(exc)
    nested_error = body.get("error")
    if isinstance(nested_error, dict):
        code = nested_error.get("code")
        if isinstance(code, str):
            return code

    code = getattr(exc, "code", None)
    return code if isinstance(code, str) else None


def extract_error_message(exc: Exception) -> str:
    """Extract a human-readable error message from a provider SDK exception."""
    body = extract_error_body(exc)
    nested_error = body.get("error")
    if isinstance(nested_error, dict):
        message = nested_error.get("message")
        if isinstance(message, str):
            return message

    return str(exc)


def normalise_provider_error(model: ModelName, exc: Exception) -> ProviderRequestError:
    """Map a raw SDK exception to a typed ProviderRequestError with retry and billing metadata."""
    provider = provider_name(model)
    model_label = user_model_name(model)
    status_code = extract_status_code(exc)
    code = extract_error_code(exc)
    message = extract_error_message(exc)
    text = f"{code or ''} {message}".lower()

    if (
        "insufficient_quota" in text
        or "credit balance" in text
        or "purchase credits" in text
        or "billing" in text
    ):
        return ProviderRequestError(
            f"{model_label} billing issue. Add credits or use mock mode.",
            provider=provider,
            status_code=status_code,
            code=code or "billing_error",
            retryable=False,
        )

    if status_code == 429:
        return ProviderRequestError(
            f"{model_label} limit reached. Try again soon.",
            provider=provider,
            status_code=status_code,
            code=code,
            retryable=True,
        )

    return ProviderRequestError(
        f"{provider} request failed: {message}",
        provider=provider,
        status_code=status_code,
        code=code,
        retryable=True,
    )


def _extract_requirement_from_prompt(prompt: PromptMessages) -> str:
    match = re.search(r"Requirement:\s*(.+?)\n\nRespond", prompt.user, flags=re.DOTALL)
    if match is None:
        return prompt.user

    value = match.group(1).strip()
    try:
        return str(json.loads(value))
    except json.JSONDecodeError:
        return value.strip('"')


def _mock_ambiguity_response(prompt: PromptMessages) -> str:
    requirement = _extract_requirement_from_prompt(prompt).lower()
    is_ambiguous = any(signal in requirement for signal in AMBIGUITY_SIGNALS)
    return json.dumps(
        {
            "label": "ambiguous" if is_ambiguous else "not_ambiguous",
            "confidence": "medium" if is_ambiguous else "high",
            "explanation": (
                "Mock analysis: the wording may need analyst review."
                if is_ambiguous
                else "Mock analysis: the requirement is specific enough for this dry run."
            ),
            "suggestion": (
                "Rewrite with measurable criteria and one clear interpretation."
                if is_ambiguous
                else ""
            ),
        },
    )


def _mock_inconsistency_response(prompt: PromptMessages) -> str:
    lowered = prompt.user.lower()
    has_signal = sum(1 for signal in INCONSISTENCY_SIGNALS if signal in lowered) >= 2
    return json.dumps(
        {
            "inconsistencies_found": has_signal,
            "pairs": [],
        },
    )


class LlmClient:
    """Client wrapper for mock, OpenAI, and Anthropic completions."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def complete(self, model: ModelName, prompt: PromptMessages) -> str:
        """Dispatch a single completion request to the mock, OpenAI, or Anthropic backend."""
        if not self._settings.use_real_llm:
            if "inconsistencies_found" in prompt.user:
                return _mock_inconsistency_response(prompt)

            return _mock_ambiguity_response(prompt)

        if model == "claude":
            return await self._complete_claude(prompt)

        return await self._complete_openai(prompt)

    async def _complete_openai(self, prompt: PromptMessages) -> str:
        if not self._settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is missing.")

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._settings.openai_api_key)
        response = await client.chat.completions.create(
            model=self._settings.openai_model,
            messages=[
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": prompt.user},
            ],
            temperature=self._settings.llm_temperature,
            max_completion_tokens=self._settings.llm_max_tokens,
        )
        return response.choices[0].message.content or ""

    async def _complete_claude(self, prompt: PromptMessages) -> str:
        if not self._settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is missing.")

        from anthropic import AsyncAnthropic
        from anthropic.types import TextBlock

        client = AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        response = await client.messages.create(
            model=self._settings.claude_model,
            system=prompt.system,
            messages=[{"role": "user", "content": prompt.user}],
            temperature=self._settings.llm_temperature,
            max_tokens=self._settings.llm_max_tokens,
        )
        text_blocks: list[str] = []
        for block in response.content:
            if getattr(block, "type", "") == "text":
                text_blocks.append(cast(TextBlock, block).text)

        return "\n".join(text_blocks)

    async def complete_with_retries(self, model: ModelName, prompt: PromptMessages) -> str:
        """Attempt a completion up to max_retries times with exponential back-off."""
        last_error: Exception | None = None
        for attempt in range(self._settings.llm_max_retries):
            try:
                return await self.complete(model, prompt)
            except ProviderRequestError as exc:
                last_error = exc
                if not exc.retryable:
                    raise
            except Exception as exc:  # pylint: disable=broad-exception-caught
                provider_error = normalise_provider_error(model, exc)
                last_error = provider_error
                if not provider_error.retryable:
                    raise provider_error from exc

            if attempt < self._settings.llm_max_retries - 1:
                await asyncio.sleep(min(2**attempt, 8))

        raise RuntimeError(str(last_error)) from last_error
