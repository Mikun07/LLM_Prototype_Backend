"""Builds system and user prompt messages for LLM smell analysis."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.models import RequirementRow

#: Prompt schema version embedded in every PromptMessages instance.
#: Increment when the system or user prompt wording changes in a way that
#: could alter LLM output, so logged responses can be traced back to the
#: exact prompt that produced them.
PROMPT_VERSION = "2.1"

AMBIGUITY_SYSTEM_MESSAGE = """
You are a professor and requirements quality analyst specialising in detecting defects in
natural-language software requirements specifications.

Your task is to analyse a SINGLE software requirement and determine whether it contains a
true ambiguity defect.

A requirement is ambiguous ONLY if:
- a competent analyst, designer, or developer could reasonably interpret the SAME statement
  in two or more different ways,
AND
- those interpretations could lead to different implementations or behaviours.

Do NOT classify a requirement as ambiguous merely because:
- implementation details are omitted
- the requirement is incomplete
- technical details are unspecified
- nonfunctional constraints are absent
- assumptions must be made using normal domain knowledge

Assume reasonable domain knowledge and standard software engineering conventions.

Be conservative when labelling ambiguity.
If the ambiguity is weak, speculative, or unlikely to affect implementation,
classify it as "not_ambiguous".

You must respond with valid JSON only.
Do not include markdown, explanations outside JSON, or extra text.
""".strip()

INCONSISTENCY_SYSTEM_MESSAGE = """
You are a professor and expert requirements quality analyst specialising in detecting defects
in natural-language software requirements specifications.

Your task is to analyse software requirements and identify logical inconsistencies.

IMPORTANT:
- Only compare requirements belonging to the SAME project
- Never compare requirements from different projects
- Requirements from different projects are independent and must not
  be treated as inconsistent
- Compare EVERY requirement against all other requirements in the same project
- Return ALL detected inconsistency pairs

An inconsistency exists if two or more requirements:
- directly contradict each other
- impose conflicting behaviour
- define incompatible rules
- create mutually exclusive outcomes
- prevent correct implementation of another requirement

Do not report:
- differences in wording
- abstraction level differences
- incompleteness
- implementation assumptions as inconsistencies.

Identify all reasonable logical contradictions and conflicting behaviours.

If a contradiction is weak but still reasonably plausible,
report it with LOW confidence instead of ignoring it.

You must respond with valid JSON only.
Do not include markdown, explanations outside JSON, or extra text.
""".strip()


@dataclass(frozen=True)
class PromptMessages:
    """System and user prompt messages sent to an LLM provider."""

    system: str
    user: str
    version: str = PROMPT_VERSION


def sanitise_requirement_text(value: str) -> str:
    """Remove control characters and collapse whitespace in a requirement text string."""
    without_control_chars = re.sub(
        r"[\x00-\x08\x0b\x0c\x0e-\x1f]",
        " ",
        value,
    )

    return re.sub(r"\s+", " ", without_control_chars).strip()


def build_ambiguity_prompt(requirement: RequirementRow) -> PromptMessages:
    """Build a system+user prompt pair for single-requirement ambiguity analysis."""
    requirement_text = json.dumps(
        sanitise_requirement_text(requirement.text),
        ensure_ascii=False,
    )

    user = f"""
Analyse the following software requirement for ambiguity.

Examples of AMBIGUOUS requirements:
- "The system shall load pages quickly."
- "The interface should be user-friendly."
- "The user may update records."
- "The system shall notify the manager when necessary."

Why ambiguous:
- subjective wording
- unclear conditions
- optional behaviour
- multiple reasonable interpretations

Examples of NOT ambiguous requirements:
- "The system shall export reports in PDF format."
- "The ATM shall eject the card after 30 seconds."
- "The application shall require email verification before login."
- "The system shall store passwords using SHA-256 hashing."

Requirement:
{requirement_text}

Decision rules:
- Missing detail alone does NOT mean ambiguity
- Incompleteness is NOT ambiguity
- Use reasonable domain assumptions
- Only classify as ambiguous if multiple reasonable interpretations
  could produce different implementations

Respond with this exact JSON structure and no other text:
{{
  "label": "ambiguous" or "not_ambiguous",
  "confidence": "high" or "medium" or "low",
  "ambiguity_type": "lexical" or "syntactic" or "referential" or "semantic" or "none",
  "explanation": "Clear explanation of the decision.",
  "suggestion": "Rewrite that removes ambiguity. Empty string if not ambiguous."
}}
""".strip()

    return PromptMessages(
        system=AMBIGUITY_SYSTEM_MESSAGE,
        user=user,
    )


def build_inconsistency_prompt(
    project_name: str,
    requirements: list[RequirementRow],
) -> PromptMessages:
    """Build a system+user prompt pair for multi-requirement inconsistency analysis."""
    payload = [
        {
            "id": requirement.id,
            "text": sanitise_requirement_text(requirement.text),
            "domain": requirement.domain,
            "project": requirement.project,
        }
        for requirement in requirements
    ]

    requirements_json = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )

    user = f"""
Analyse the following software requirements for logical inconsistencies.

Project:
{project_name}

IMPORTANT:
- All requirements belong to the SAME project
- Only compare requirements inside this project
- Ignore contradictions between different projects
- Compare EVERY requirement against all other requirements in this project
- Identify all reasonable contradictions, conflicting behaviours,
incompatible rules, and mutually exclusive requirements
- Return ALL detected inconsistency pairs

Requirements:
{requirements_json}

Examples of inconsistencies:
- Req A: "Password reset shall not require authentication."
- Req B: "All password changes shall require authentication."

- Req A: "Users shall be automatically logged out after 5 minutes."
- Req B: "Users shall remain logged in indefinitely."

- Req A: "Only administrators shall delete users."
- Req B: "All authenticated users shall be able to delete users."

- Req A: "Orders shall be processed automatically."
- Req B: "Orders shall require manual approval before processing."

- Req A: "Users shall remain logged in for 30 days."
- Req B: "Users shall be logged out after 5 minutes of inactivity."

Examples of NOT inconsistencies:
- Different wording describing the same behaviour
- Different abstraction levels
- Missing implementation details
- Requirements belonging to different projects

Decision rules:
- Compare each requirement with every other requirement in the project
- Report inconsistencies when requirements contradict,
  conflict logically, or define incompatible behaviour
- Different abstraction levels are NOT inconsistencies
- Missing information is NOT inconsistency
- Different wording alone is NOT inconsistency
- Cross-project contradictions must be ignored

If a contradiction is weak but still reasonably plausible,
report it with LOW confidence instead of ignoring it.

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
      "explanation": "Explanation of the contradiction.",
      "suggestion": "Suggested resolution."
    }}
  ]
}}
""".strip()

    return PromptMessages(
        system=INCONSISTENCY_SYSTEM_MESSAGE,
        user=user,
    )
