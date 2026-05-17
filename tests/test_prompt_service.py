"""Tests for the prompt builder functions."""

from __future__ import annotations

from app.models import RequirementRow
from app.services.prompt_service import build_ambiguity_prompt, build_inconsistency_prompt


def test_ambiguity_prompt_requests_json() -> None:
    """Verify that the ambiguity prompt instructs JSON-only output and embeds the requirement."""
    prompt = build_ambiguity_prompt(
        RequirementRow(id="REQ-1", text='The system may show "fast" results.'),
    )

    assert "valid JSON only" in prompt.system
    assert '"label": "ambiguous" or "not_ambiguous"' in prompt.user
    assert '\\"fast\\"' in prompt.user


def test_inconsistency_prompt_includes_no_result_shape() -> None:
    """Verify that the inconsistency prompt includes the empty-pairs JSON template."""
    prompt = build_inconsistency_prompt(
        "Authentication Project",
        [
            RequirementRow(id="REQ-1", text="The system shall require authentication."),
            RequirementRow(
                id="REQ-2",
                text="The system shall allow access without authentication.",
            ),
        ],
    )

    assert '"inconsistencies_found": false' in prompt.user
    assert '"pairs": []' in prompt.user
    assert "REQ-1" in prompt.user
    assert "Authentication Project" in prompt.user
