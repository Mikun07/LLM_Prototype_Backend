"""Tests for runtime configuration defaults."""

from __future__ import annotations

from pytest import MonkeyPatch

from app.config import get_settings


def test_raw_llm_response_logging_is_disabled_by_default(monkeypatch: MonkeyPatch) -> None:
    """Verify that sensitive raw model output is not logged unless explicitly enabled."""
    monkeypatch.delenv("LOG_RAW_LLM_RESPONSES", raising=False)
    get_settings.cache_clear()

    assert get_settings().log_raw_llm_responses is False
