import json
from app.database.connection import get_connection


def initialize_module2_tables():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS psychological_profiles (
                persona_id INTEGER PRIMARY KEY,
                profile_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS interview_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                persona_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS survey_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                persona_id INTEGER NOT NULL,
                survey_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        connection.execute("""
            CREATE TABLE IF NOT EXISTS persona_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                persona_id INTEGER NOT NULL,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                source_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_persona_memories_persona
            ON persona_memories(persona_id, created_at)
        """)
        
        connection.execute("""
            CREATE TABLE IF NOT EXISTS consistency_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                persona_id INTEGER NOT NULL,
                report_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
    


def save_profile(profile):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO psychological_profiles
                (persona_id, profile_json)
            VALUES (?, ?)
            ON CONFLICT(persona_id) DO UPDATE SET
                profile_json = excluded.profile_json,
                created_at = CURRENT_TIMESTAMP
        """, (
            profile.persona_id,
            profile.model_dump_json(),
        ))


def get_profile(persona_id: int):
    with get_connection() as connection:
        row = connection.execute("""
            SELECT profile_json
            FROM psychological_profiles
            WHERE persona_id = ?
        """, (persona_id,)).fetchone()

    return json.loads(row["profile_json"]) if row else None


def save_interview_response(persona_id, question, response):
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO interview_responses
                (persona_id, question, response)
            VALUES (?, ?, ?)
        """, (persona_id, question, response))

        response_id = cursor.lastrowid

        connection.execute("""
            INSERT INTO persona_memories
                (persona_id, memory_type, content, source_id)
            VALUES (?, ?, ?, ?)
        """, (
            persona_id,
            "interview",
            json.dumps({
                "question": question,
                "response": response,
            }, ensure_ascii=False),
            response_id,
        ))

        return response_id


def save_survey_response(persona_id, survey):
    survey_json = json.dumps(survey, ensure_ascii=False)

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO survey_responses
                (persona_id, survey_json)
            VALUES (?, ?)
        """, (persona_id, survey_json))

        response_id = cursor.lastrowid

        connection.execute("""
            INSERT INTO persona_memories
                (persona_id, memory_type, content, source_id)
            VALUES (?, ?, ?, ?)
        """, (
            persona_id,
            "survey",
            survey_json,
            response_id,
        ))

        return response_id
    
def save_persona_memory(
    persona_id: int,
    memory_type: str,
    content: str,
    source_id: int | None = None,
):
    """Store a persistent memory for a synthetic persona."""
    if not content or not content.strip():
        raise ValueError("Memory content cannot be empty")

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO persona_memories
                (persona_id, memory_type, content, source_id)
            VALUES (?, ?, ?, ?)
        """, (
            persona_id,
            memory_type,
            content.strip(),
            source_id,
        ))

        return cursor.lastrowid


def get_persona_memories(
    persona_id: int,
    limit: int = 20,
    memory_type: str | None = None,
):
    """Retrieve recent memories for a persona, oldest first in the result."""
    if limit < 1 or limit > 200:
        raise ValueError("limit must be between 1 and 200")

    with get_connection() as connection:
        if memory_type:
            rows = connection.execute("""
                SELECT id, persona_id, memory_type, content,
                       source_id, created_at
                FROM persona_memories
                WHERE persona_id = ? AND memory_type = ?
                ORDER BY id DESC
                LIMIT ?
            """, (persona_id, memory_type, limit)).fetchall()
        else:
            rows = connection.execute("""
                SELECT id, persona_id, memory_type, content,
                       source_id, created_at
                FROM persona_memories
                WHERE persona_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (persona_id, limit)).fetchall()

    # Return chronological order for use as conversation history.
    return [dict(row) for row in reversed(rows)]


def get_interview_responses(persona_id: int, limit: int = 50):
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, question, response, created_at
            FROM interview_responses
            WHERE persona_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (persona_id, limit)).fetchall()

    return [dict(row) for row in reversed(rows)]


def get_survey_responses(persona_id: int, limit: int = 50):
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, survey_json, created_at
            FROM survey_responses
            WHERE persona_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (persona_id, limit)).fetchall()

    results = []
    for row in rows:
        item = dict(row)
        try:
            item["survey"] = json.loads(item["survey_json"])
        except (json.JSONDecodeError, TypeError):
            item["survey"] = item["survey_json"]
        results.append(item)

    return list(reversed(results))


def save_consistency_report(persona_id: int, report: dict):
    report_json = json.dumps(report, ensure_ascii=False)

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO consistency_reports (persona_id, report_json)
            VALUES (?, ?)
        """, (persona_id, report_json))

        return cursor.lastrowid


def get_latest_consistency_report(persona_id: int):
    with get_connection() as connection:
        row = connection.execute("""
            SELECT id, persona_id, report_json, created_at
            FROM consistency_reports
            WHERE persona_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (persona_id,)).fetchone()

    if row is None:
        return None

    result = dict(row)
    result["report"] = json.loads(result.pop("report_json"))
    return result