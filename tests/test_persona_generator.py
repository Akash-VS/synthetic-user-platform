
from app.services.persona_generator import generate_persona

persona = generate_persona(
    role="Frontend Developer",
    experience="Intermediate",
    goal="Inspect Figma designs and implement them in code",
)

print(persona.model_dump_json(indent=2))
