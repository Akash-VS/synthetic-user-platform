
from app.services.persona_generator import generate_persona
from app.database.repository import save_persona


def create_persona(role: str, experience: str, goal: str):
    persona = generate_persona(role, experience, goal)
    save_persona(persona)
    return persona
