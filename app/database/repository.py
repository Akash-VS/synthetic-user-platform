
from app.database.connection import get_connection


def save_persona(persona):
    data = persona.model_dump()

    # Convert lists into strings for SQLite storage
    for key, value in data.items():
        if isinstance(value, list):
            data[key] = ", ".join(str(item) for item in value)
        elif value is None:
            data[key] = ""

    # Prepare column definitions separately
    column_definitions = [
        f'"{key}" TEXT' for key in data
    ]
    columns_sql = ", ".join(column_definitions)
    columns = ", ".join(f'"{key}"' for key in data)
    placeholders = ", ".join("?" for _ in data)

    with get_connection() as connection:
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS generated_personas (
                persona_id INTEGER PRIMARY KEY AUTOINCREMENT,
                {columns_sql}
            )
            """
        )

        connection.execute(
            f"INSERT INTO generated_personas ({columns}) "
            f"VALUES ({placeholders})",
            tuple(data.values()),
        )

    return "Persona saved successfully"


def list_personas(limit: int = 50, offset: int = 0):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM generated_personas
            ORDER BY persona_id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

    return [dict(row) for row in rows]


def get_persona(persona_id: int):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT * FROM generated_personas
            WHERE persona_id = ?
            """,
            (persona_id,),
        ).fetchone()

    return dict(row) if row else None


#from app.database.connection import get_connection


def archive_persona(persona_id: int):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE generated_personas
            SET persona_status = 'archived'
            WHERE persona_id = ?
              AND persona_status = 'active'
            """,
            (persona_id,),
        )
        return cursor.rowcount > 0
    

def update_persona(persona_id: int, updates: dict):
    allowed_fields = {
        "role",
        "experience_level",
        "skills",
        "goals",
        "preferences",
        "challenges",
        "working_style",
    }

    updates = {
        key: value
        for key, value in updates.items()
        if key in allowed_fields and value is not None
    }

    if not updates:
        return False

    for key, value in updates.items():
        if isinstance(value, list):
            updates[key] = ", ".join(str(item) for item in value)

    fields = ", ".join(f'"{key}" = ?' for key in updates)
    values = list(updates.values()) + [persona_id]

    with get_connection() as connection:
        cursor = connection.execute(
            f"""
            UPDATE generated_personas
            SET {fields}
            WHERE persona_id = ?
              AND persona_status = 'active'
            """,
            values,
        )

        return cursor.rowcount > 0
    

def get_generation_context(role: str, goal: str):
    with get_connection() as connection:
        personas = connection.execute(
            """
            SELECT persona_label, archetype, role, experience_level,
                   relevant_skills, goals, preferences,
                   behavioral_traits, usability_needs
            FROM personas
            WHERE role LIKE ?
               OR archetype LIKE ?
               OR goals LIKE ?
               OR relevant_skills LIKE ?
            LIMIT 3
            """,
            (f"%{role}%", f"%{role}%", f"%{goal}%", f"%{role}%"),
        ).fetchall()

        sources = connection.execute(
            """
            SELECT source_title, source_url, research_topic,
                   key_finding_or_summary, limitations
            FROM research_sources
            WHERE research_topic LIKE ?
               OR key_finding_or_summary LIKE ?
               OR relevance_to_milestone LIKE ?
            LIMIT 3
            """,
            (f"%{goal}%", f"%{goal}%", f"%{goal}%"),
        ).fetchall()

    return {
        "existing_personas": [dict(row) for row in personas],
        "research_sources": [dict(row) for row in sources],
    }

def restore_persona(persona_id: int):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE generated_personas
            SET persona_status = 'active'
            WHERE persona_id = ?
              AND persona_status = 'archived'
            """,
            (persona_id,),
        )

        return cursor.rowcount > 0



