from __future__ import annotations

from app.services.response_parser import parse_ambiguity_response, parse_inconsistency_response


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


def test_parse_ambiguity_legacy_response() -> None:
    """Verify that a legacy yes/no ambiguity response is parsed via the regex fallback."""
    parsed = parse_ambiguity_response("Ambiguous: No\nExplanation: Clear enough")

    assert parsed.label == "not_ambiguous"
    assert parsed.explanation == "Clear enough"


def test_parse_inconsistency_json_response() -> None:
    """Verify that a well-formed JSON inconsistency response is parsed correctly."""
    parsed = parse_inconsistency_response(
        '{"inconsistencies_found":true,"pairs":[{"req_a_id":"REQ-1","req_b_id":"REQ-2",'
        '"label":"inconsistent","confidence":"medium","explanation":"Conflict."}]}',
    )

    assert parsed.inconsistencies_found is True
    assert parsed.pairs[0].confidence == "MEDIUM"
