
import os
import json

from dotenv import load_dotenv
from google import genai

from app.database.repository import get_persona
from app.database.module2_repository import (
    get_profile,
    get_persona_memories,
    save_interview_response,
)

load_dotenv()


def generate_interview_response(persona_id: int, question: str):
    persona = get_persona(persona_id)

    if persona is None:
        raise ValueError("Persona not found")

    profile = get_profile(persona_id)

    if profile is None:
        raise ValueError("Generate a psychological profile first")

    # Retrieve previous preferences, interviews, and survey answers.
    memories = get_persona_memories(persona_id, limit=30)

    keys = [
        key.strip()
        for key in os.getenv("GEMINI_API_KEYS", "").split(",")
        if key.strip()
    ]
    model = os.getenv("GEMINI_MODEL")

    if not keys or not model:
        raise ValueError("Gemini configuration is missing")

    client = genai.Client(api_key=keys[0])

    memory_context = json.dumps(
        memories,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    prompt = f"""
You are simulating a fictional user for product design research.

PERSONA:
{persona}

PSYCHOLOGICAL PROFILE:
{profile}

PREVIOUS MEMORIES AND INTERACTIONS:
{memory_context}

NEW INTERVIEW QUESTION:
{question}

Instructions:
1. Answer naturally from this persona's perspective.
2. Use the psychological profile and relevant stored memories.
3. Maintain continuity with previous answers and preferences.
4. Do not force irrelevant memories into the answer.
5. If a previous preference conflicts with the current question,
   acknowledge the nuance instead of inventing a resolution.
6. A persona may change their mind; do not treat every change
   as an error.
7. Do not invent personal experiences as verified facts.
8. Return only the simulated answer.
"""

    result = client.models.generate_content(
        model=model,
        contents=prompt,
    )

    if not result.text:
        raise RuntimeError("Gemini returned an empty response")

    answer = result.text.strip()

    response_id = save_interview_response(
        persona_id,
        question,
        answer,
    )

    return {
        "persona_id": persona_id,
        "question": question,
        "response": answer,
        "response_id": response_id,
        "is_synthetic": True,
    }
