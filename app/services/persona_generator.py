
import os
import json

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field
from app.database.repository import get_generation_context

load_dotenv()


class Persona(BaseModel):
    role: str
    experience_level: str
    skills: list[str]
    goals: list[str]
    preferences: list[str]
    challenges: list[str]
    working_style: str


def generate_persona(role: str, experience: str, goal: str) -> Persona:
    keys = [
        key.strip()
        for key in os.getenv("GEMINI_API_KEYS", "").split(",")
        if key.strip()
    ]

    if not keys:
        raise ValueError("Configure GEMINI_API_KEYS in .env")

    model = os.getenv("GEMINI_MODEL")
    if not model:
        raise ValueError("Configure GEMINI_MODEL in .env")
    
    context = get_generation_context(role, goal)
    context_json = json.dumps(context, indent=2)

    

    prompt = f"""
        Generate one fictional synthetic Figma user persona.

        User input:
        - Role: {role}
        - Experience: {experience}
        - Goal: {goal}

        Retrieved context from SQLite:
        {context_json}

        Instructions:
        1. Use the retrieved personas as reference for relevant skills,
        goals, preferences, usability needs, and working styles.
        2. Create a new persona tailored to the requested role and goal.
        3. Do not copy an existing persona verbatim.
        4. Use the research sources only when they are available.
        5. Do not invent research findings or claim unsupported facts.
        6. Clearly treat the generated persona as synthetic, not a real person.

        Return valid JSON with exactly these fields:
        role, experience_level, skills, goals,
        preferences, challenges, working_style.

        Skills, goals, preferences, and challenges must be lists
        of strings. All other fields must be strings.
        """



    # Use the first configured key. Don't rotate keys to bypass
    # rate limits or quotas.
    client = genai.Client(api_key=keys[0])

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty response")

    data = json.loads(response.text)
    return Persona.model_validate(data)
