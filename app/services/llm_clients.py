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
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def complete(self, model: ModelName, prompt: PromptMessages) -> str:
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
            max_tokens=self._settings.llm_max_tokens,
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
        last_error: Exception | None = None
        for attempt in range(self._settings.llm_max_retries):
            try:
                return await self.complete(model, prompt)
            except Exception as exc:  # pragma: no cover - live API path
                last_error = exc
                await asyncio.sleep(min(2**attempt, 8))

        raise RuntimeError(f"LLM request failed after retries: {last_error}") from last_error
