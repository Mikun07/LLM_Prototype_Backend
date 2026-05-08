from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.models import RequirementRow

PROMPT_VERSION = "1.0"

AMBIGUITY_SYSTEM_MESSAGE = """
You are an expert requirements quality analyst specialising in detecting defects in
natural-language software requirements specifications. Your task is to analyse a single
software requirement and determine whether it contains an ambiguity smell.

You must respond with valid JSON only. Do not include any text, explanation, or markdown
outside the JSON object.
""".strip()

INCONSISTENCY_SYSTEM_MESSAGE = """
You are an expert requirements quality analyst specialising in detecting defects in
natural-language software requirements specifications. Your task is to analyse a set of
requirements from the same system and identify any inconsistencies between them.

You must respond with valid JSON only. Do not include any text, explanation, or markdown
outside the JSON object.
""".strip()


@dataclass(frozen=True)
class PromptMessages:
    system: str
    user: str
    version: str = PROMPT_VERSION


def sanitise_requirement_text(value: str) -> str:
    without_control_chars = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", value)
    return re.sub(r"\s+", " ", without_control_chars).strip()


def build_ambiguity_prompt(requirement: RequirementRow) -> PromptMessages:
    requirement_text = json.dumps(
        sanitise_requirement_text(requirement.text),
        ensure_ascii=False,
    )
    user = f"""
Analyse the following software requirement for ambiguity.

A requirement is AMBIGUOUS if a requirements analyst who is familiar with the domain could
interpret it in two or more ways, such that different designers or implementers could produce
different designs or implementations. This includes lexical ambiguity, syntactic ambiguity,
and unclear references.

Requirement:
{requirement_text}

Respond with this exact JSON structure and no other text:
{{
  "label": "ambiguous" or "not_ambiguous",
  "confidence": "high" or "medium" or "low",
  "explanation": "A clear explanation of why this requirement is or is not ambiguous.",
  "suggestion": "A proposed reformulation that resolves the ambiguity. Empty string if clean."
}}
""".strip()

    return PromptMessages(system=AMBIGUITY_SYSTEM_MESSAGE, user=user)


def build_inconsistency_prompt(requirements: list[RequirementRow]) -> PromptMessages:
    payload = [
        {
            "id": requirement.id,
            "text": sanitise_requirement_text(requirement.text),
            "domain": requirement.domain,
            "project": requirement.project,
        }
        for requirement in requirements
    ]
    requirements_json = json.dumps(payload, ensure_ascii=False, indent=2)
    user = f"""
Analyse the following set of software requirements for inconsistencies.

Two or more requirements are INCONSISTENT if satisfying one requirement necessarily violates
another. Their constraints directly contradict each other, making it impossible to satisfy
all requirements simultaneously.

Example of inconsistency:
  Req A: "The system shall allow password reset without authentication."
  Req B: "The system shall require authentication for all password changes."

Requirements from the same project and domain:
{requirements_json}

If NO inconsistencies are found, respond with:
{{
  "inconsistencies_found": false,
  "pairs": []
}}

If inconsistencies ARE found, respond with:
{{
  "inconsistencies_found": true,
  "pairs": [
    {{
      "req_a_id": "REQ-001",
      "req_b_id": "REQ-002",
      "label": "inconsistent",
      "confidence": "high" or "medium" or "low",
      "explanation": "A clear explanation of the contradiction.",
      "suggestion": "A proposed resolution."
    }}
  ]
}}
""".strip()

    return PromptMessages(system=INCONSISTENCY_SYSTEM_MESSAGE, user=user)
