
import json
import os

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

from app.database.repository import get_persona
from app.database.module2_repository import (
    get_profile,
    get_persona_memories,
    save_survey_response,
)

load_dotenv()


class SurveyQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    question_type: str = "text"
    options: list[str] = Field(default_factory=list)


def generate_survey_response(
    persona_id: int,
    questions: list[SurveyQuestion],
):
    persona = get_persona(persona_id)

    if persona is None:
        raise ValueError("Persona not found")

    profile = get_profile(persona_id)

    if profile is None:
        raise ValueError("Generate a psychological profile first")

    # Retrieve prior preferences, interview answers, and survey answers.
    memories = get_persona_memories(persona_id, limit=30)

    keys = [
        key.strip()
        for key in os.getenv("GEMINI_API_KEYS", "").split(",")
        if key.strip()
    ]
    model = os.getenv("GEMINI_MODEL")

    if not keys or not model:
        raise ValueError("Gemini configuration is missing")

    survey_questions = [
        question.model_dump() for question in questions
    ]

    memory_context = json.dumps(
        memories,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    prompt = f"""
Simulate survey answers for a fictional product user.

PERSONA:
{json.dumps(persona, ensure_ascii=False, default=str)}

PSYCHOLOGICAL PROFILE:
{json.dumps(profile, ensure_ascii=False, default=str)}

PREVIOUS MEMORIES AND INTERACTIONS:
{memory_context}

NEW SURVEY QUESTIONS:
{json.dumps(survey_questions, ensure_ascii=False)}

Instructions:
1. Answer every question in the supplied order.
2. Respect the question options when provided.
3. Keep answers consistent with relevant persona preferences
   and previous interactions.
4. Do not force irrelevant memories into an answer.
5. If preferences have changed, allow for a reasonable change
   rather than inventing a contradiction.
6. Never select an answer outside the supplied options.
7. Return a JSON object with an "answers" array.
8. Each answer must contain "question" and "answer".
9. Every answer must be a string.
10. These are synthetic responses, not real user research data.
"""

    client = genai.Client(api_key=keys[0])

    result = client.models.generate_content(
        model=model,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )

    if not result.text:
        raise RuntimeError("Gemini returned an empty response")

    try:
        data = json.loads(result.text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Gemini returned invalid survey JSON"
        ) from exc

    if (
        not isinstance(data, dict)
        or not isinstance(data.get("answers"), list)
        or len(data["answers"]) != len(questions)
    ):
        raise ValueError("Invalid survey response structure")

    for item, question in zip(data["answers"], questions):
        if not isinstance(item, dict):
            raise ValueError("Invalid survey answer")

        if item.get("question") != question.question:
            raise ValueError("Survey question order mismatch")

        if not isinstance(item.get("answer"), str):
            raise ValueError("Survey answers must be strings")

        if question.options and item["answer"] not in question.options:
            raise ValueError(
                "Answer is not one of the allowed options"
            )

    response_id = save_survey_response(persona_id, data)

    return {
        "persona_id": persona_id,
        "answers": data["answers"],
        "response_id": response_id,
        "is_synthetic": True,
    }
