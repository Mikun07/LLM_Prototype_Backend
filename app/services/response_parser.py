from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ValidationError

from app.models import ConfidenceLevel

AmbiguityDecisionLabel = Literal["ambiguous", "not_ambiguous", "parse_error"]


class ParsedAmbiguity(BaseModel):
    label: AmbiguityDecisionLabel
    confidence: ConfidenceLevel
    explanation: str
    suggestion: str = ""


class ParsedInconsistencyPair(BaseModel):
    req_a_id: str
    req_b_id: str
    label: Literal["inconsistent", "consistent", "parse_error"]
    confidence: ConfidenceLevel
    explanation: str
    suggestion: str = ""


class ParsedInconsistency(BaseModel):
    inconsistencies_found: bool
    pairs: list[ParsedInconsistencyPair]


def normalise_confidence(value: object) -> ConfidenceLevel:
    text = str(value or "low").strip().upper()
    if text in {"HIGH", "MEDIUM", "LOW"}:
        return text  # type: ignore[return-value]

    return "LOW"


def extract_json(raw: str) -> object:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if match is None:
            raise

        return json.loads(match.group(0))


def parse_yes_no(value: str) -> bool | None:
    lowered = value.strip().lower()
    if lowered in {"yes", "y", "true", "ambiguous", "inconsistent"}:
        return True
    if lowered in {"no", "n", "false", "not_ambiguous", "consistent"}:
        return False

    return None


def parse_ambiguity_response(raw: str) -> ParsedAmbiguity:
    try:
        parsed = extract_json(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Expected a JSON object.")

        label = str(parsed.get("label", "")).strip().lower()
        if label not in {"ambiguous", "not_ambiguous"}:
            yes_no = parse_yes_no(label)
            label = "ambiguous" if yes_no else "not_ambiguous"

        return ParsedAmbiguity(
            label=label,  # type: ignore[arg-type]
            confidence=normalise_confidence(parsed.get("confidence")),
            explanation=str(parsed.get("explanation") or "No explanation supplied."),
            suggestion=str(parsed.get("suggestion") or ""),
        )
    except (ValidationError, ValueError, json.JSONDecodeError):
        match = re.search(r"Ambigu(?:ity|ous)\s*:\s*(yes|no)", raw, flags=re.IGNORECASE)
        if match is not None:
            is_ambiguous = parse_yes_no(match.group(1)) is True
            explanation_match = re.search(
                r"Explanation\s*:\s*(.+)",
                raw,
                flags=re.IGNORECASE | re.DOTALL,
            )
            return ParsedAmbiguity(
                label="ambiguous" if is_ambiguous else "not_ambiguous",
                confidence="LOW",
                explanation=(
                    explanation_match.group(1).strip()
                    if explanation_match is not None
                    else "Parsed from legacy yes/no response."
                ),
                suggestion="",
            )

        return ParsedAmbiguity(
            label="parse_error",
            confidence="LOW",
            explanation=f"Unable to parse LLM response: {raw}",
            suggestion="Review the raw response and rerun this requirement.",
        )


def parse_inconsistency_response(raw: str) -> ParsedInconsistency:
    try:
        parsed = extract_json(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Expected a JSON object.")

        pairs = [
            ParsedInconsistencyPair(
                req_a_id=str(pair.get("req_a_id") or pair.get("reqAId") or ""),
                req_b_id=str(pair.get("req_b_id") or pair.get("reqBId") or ""),
                label=str(pair.get("label") or "inconsistent").lower(),  # type: ignore[arg-type]
                confidence=normalise_confidence(pair.get("confidence")),
                explanation=str(pair.get("explanation") or "No explanation supplied."),
                suggestion=str(pair.get("suggestion") or ""),
            )
            for pair in parsed.get("pairs", [])
            if isinstance(pair, dict)
        ]
        return ParsedInconsistency(
            inconsistencies_found=bool(parsed.get("inconsistencies_found", bool(pairs))),
            pairs=pairs,
        )
    except (ValidationError, ValueError, json.JSONDecodeError):
        match = re.search(r"Inconsisten(?:cy|t)\s*:\s*(yes|no)", raw, flags=re.IGNORECASE)
        if match is not None:
            return ParsedInconsistency(
                inconsistencies_found=parse_yes_no(match.group(1)) is True,
                pairs=[],
            )

        return ParsedInconsistency(
            inconsistencies_found=True,
            pairs=[
                ParsedInconsistencyPair(
                    req_a_id="",
                    req_b_id="",
                    label="parse_error",
                    confidence="LOW",
                    explanation=f"Unable to parse LLM response: {raw}",
                    suggestion="Review the raw response and rerun this requirement group.",
                ),
            ],
        )
