"""Tests for the LLM response parser."""

from __future__ import annotations

from app.services.response_parser import (
    normalise_ambiguity_type,
    parse_ambiguity_response,
    parse_inconsistency_response,
)


def test_parse_ambiguity_json_response() -> None:
    """Verify that a well-formed JSON ambiguity response is parsed correctly."""
    raw_response = (
        '{"label":"ambiguous","confidence":"high","explanation":"Vague term.",'
        '"suggestion":"Be specific."}'
    )

    parsed = parse_ambiguity_response(
        raw_response,
    )

    assert parsed.label == "ambiguous"
    assert parsed.confidence == "HIGH"
    assert parsed.ambiguity_type == "none"


def test_parse_ambiguity_type_captured() -> None:
    """Verify that ambiguity_type is captured from the LLM response when present."""
    raw_response = (
        '{"label":"ambiguous","confidence":"medium","ambiguity_type":"lexical",'
        '"explanation":"The term has multiple meanings.","suggestion":"Clarify the term."}'
    )

    parsed = parse_ambiguity_response(raw_response)

    assert parsed.ambiguity_type == "lexical"


def test_parse_ambiguity_type_unknown_defaults_to_none() -> None:
    """Verify that an unrecognised ambiguity_type value defaults to none."""
    assert normalise_ambiguity_type("structural") == "none"
    assert normalise_ambiguity_type(None) == "none"
    assert normalise_ambiguity_type("LEXICAL") == "lexical"


def test_parse_ambiguity_legacy_response_defaults_ambiguity_type() -> None:
    """Verify that the legacy yes/no fallback path sets ambiguity_type to none."""
    parsed = parse_ambiguity_response("Ambiguous: No\nExplanation: Clear enough")

    assert parsed.ambiguity_type == "none"


def test_parse_ambiguity_legacy_response() -> None:
    """Verify that a legacy yes/no ambiguity response is parsed via the regex fallback."""
    parsed = parse_ambiguity_response("Ambiguous: No\nExplanation: Clear enough")

    assert parsed.label == "not_ambiguous"
    assert parsed.explanation == "Clear enough"


def test_parse_ambiguity_unknown_label_returns_parse_error() -> None:
    """Verify that unknown labels are surfaced instead of silently becoming clean."""
    parsed = parse_ambiguity_response(
        '{"label":"uncertain","confidence":"medium","explanation":"Cannot decide."}',
    )

    assert parsed.label == "parse_error"
    assert parsed.confidence == "LOW"
    assert "Unable to parse LLM response" in parsed.explanation


def test_parse_inconsistency_json_response() -> None:
    """Verify that a well-formed JSON inconsistency response is parsed correctly."""
    parsed = parse_inconsistency_response(
        '{"inconsistencies_found":true,"pairs":[{"req_a_id":"REQ-1","req_b_id":"REQ-2",'
        '"label":"inconsistent","confidence":"medium","explanation":"Conflict."}]}',
    )

    assert parsed.inconsistencies_found is True
    assert parsed.pairs[0].confidence == "MEDIUM"
