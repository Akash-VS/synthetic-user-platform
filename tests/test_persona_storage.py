
from app.services.persona_service import create_persona
from app.database.connection import get_connection

persona = create_persona(
    role="UX Designer",
    experience="Intermediate",
    goal="Identify usability issues in Figma prototypes",
)

print("Generated persona:", persona.role)

with get_connection() as connection:
    count = connection.execute(
        "SELECT COUNT(*) FROM generated_personas"
    ).fetchone()[0]

print("Saved generated personas:", count)
