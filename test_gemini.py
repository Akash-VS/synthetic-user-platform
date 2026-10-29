
import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_keys = [
    key.strip()
    for key in os.getenv("GEMINI_API_KEYS", "").split(",")
    if key.strip()
]

model = os.getenv("GEMINI_MODEL", "")

if not api_keys:
    raise ValueError("No Gemini API keys found in .env")

client = genai.Client(api_key=api_keys[0])

prompt = """
Generate one fictional synthetic Figma user persona.

Requirements:
- Role: Frontend Developer
- Experience level: Intermediate
- Goal: Inspect Figma designs and implement them in code

Return a JSON object with exactly these fields:
{
    "role": "string",
    "experience_level": "string",
    "skills": ["string"],
    "goals": ["string"],
    "preferences": ["string"],
    "challenges": ["string"],
    "working_style": "string"
}

Return valid JSON only.
Do not claim this persona represents a real person.
"""

response = client.models.generate_content(
    model=model,
    contents=prompt,
    config={
        "response_mime_type": "application/json"
    },
)

persona = json.loads(response.text)

required_fields = [
    "role",
    "experience_level",
    "skills",
    "goals",
    "preferences",
    "challenges",
    "working_style",
]

for field in required_fields:
    if field not in persona:
        raise ValueError(f"Missing required field: {field}")

print("\nPersona generated successfully!\n")
print(json.dumps(persona, indent=4))
