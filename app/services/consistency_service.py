import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import Literal

from app.database.repository import get_persona
from app.database.module2_repository import (
    get_profile,
    get_persona_memories,
    get_interview_responses,
    get_survey_responses,
    save_consistency_report,
)


class ConsistencyIssue(BaseModel):
    severity: Literal["low", "medium", "high"]
    category: Literal[
        "profile_contradiction",
        "memory_contradiction",
        "history_contradiction",
        "unsupported_claim",
    ]
    current_statement: str
    conflicting_evidence: str
    explanation: str
    suggested_resolution: str


class ConsistencyReport(BaseModel):
    persona_id: int
    response_type: Literal["interview", "survey", "general"]
    overall_status: Literal[
        "consistent",
        "potential_inconsistency",
        "insufficient_context",
    ]
    consistency_score: int = Field(ge=0, le=100)
    issues: list[ConsistencyIssue] = Field(default_factory=list)
    summary: str


def validate_persona_consistency(
    persona_id: int,
    new_response: str,
    response_type: str = "general",
    ) -> ConsistencyReport:
    load_dotenv()

    persona = get_persona(persona_id)
    if persona is None:
        raise ValueError("Persona not found")

    profile = get_profile(persona_id)
    memories = get_persona_memories(persona_id, limit=50)
    interviews = get_interview_responses(persona_id, limit=30)
    surveys = get_survey_responses(persona_id, limit=20)

    api_key = (
        os.getenv("GEMINI_API_KEYS")
    )
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

    if not api_key:
        raise RuntimeError(
            "Gemini API key is missing. Set GEMINI_API_KEYS "
            "in your .env file."
        )

    client = genai.Client(api_key=api_key)

    context = {
        "persona": persona,
        "psychological_profile": profile,
        "stored_memories": memories,
        "previous_interviews": interviews,
        "previous_surveys": surveys,
    }

    prompt = f"""
You are validating consistency for a SYNTHETIC USER in a UX research
simulation. This is not a real person's psychological diagnosis.

Compare the new response with the supplied persona context.

Rules:
1. Flag a contradiction only when the evidence supports it.
2. Different opinions about different topics are not automatically
   contradictions.
3. A preference may change over time; do not automatically treat a
   change as a contradiction.
4. Do not invent conflicting evidence.
5. If there is not enough evidence, use insufficient_context.
6. Treat missing information as unknown, not as a contradiction.
7. Return only valid JSON matching the required schema.
8. consistency_score must be an integer from 0 to 100.
9. Use an empty issues list when no evidence-backed issue exists.
10. Mark a response consistent when available evidence supports it
    and no meaningful contradiction is found.

Response type:
{response_type}

New response to validate:
{new_response}

Available persona context:
{json.dumps(context, ensure_ascii=False, default=str)}

Return JSON with these fields:
{{
  "persona_id": {persona_id},
  "response_type": "{response_type}",
  "overall_status": "consistent",
  "consistency_score": 90,
  "issues": [
    {{
      "severity": "medium",
      "category": "memory_contradiction",
      "current_statement": "The relevant statement in the new response",
      "conflicting_evidence": "The exact relevant stored evidence",
      "explanation": "Why the statements may conflict",
      "suggested_resolution": "A cautious way to resolve or review it"
    }}
  ],
  "summary": "Short explanation of the result"
}}

Allowed overall_status values:
consistent, potential_inconsistency, insufficient_context

Allowed issue severity values:
low, medium, high

Allowed issue category values:
profile_contradiction, memory_contradiction,
history_contradiction, unsupported_claim
"""

    result = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )

    if not result.text:
        raise RuntimeError("Gemini returned an empty validation result")

    try:
        report = ConsistencyReport.model_validate_json(result.text)
    except Exception as exc:
        raise RuntimeError(
            "Gemini returned an invalid consistency report"
        ) from exc

    report_data = report.model_dump()
    save_consistency_report(persona_id, report_data)

    return report_data