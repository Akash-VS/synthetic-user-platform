
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "synthetic_users.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(generated_personas)"
            )
        }

        if not columns:
            raise RuntimeError(
                "generated_personas table does not exist. "
                "Run your persona storage test first."
            )

        if "persona_status" not in columns:
            connection.execute(
                """
                ALTER TABLE generated_personas
                ADD COLUMN persona_status TEXT NOT NULL DEFAULT 'active'
                """
            )

        if "created_at" not in columns:
            connection.execute(
                """
                ALTER TABLE generated_personas
                ADD COLUMN created_at TEXT
                """
            )
            
            

def get_generation_context(role: str, goal: str):
    with get_connection() as connection:
        # Find existing personas related to the requested role or goal.
        personas = connection.execute(
            """
            SELECT persona_label, archetype, role, experience_level,
                   relevant_skills, product_familiarity,
                   figma_features_in_scope, goals, preferences,
                   behavioral_traits, usability_needs
            FROM personas
            WHERE role LIKE ?
               OR archetype LIKE ?
               OR goals LIKE ?
               OR relevant_skills LIKE ?
            LIMIT 3
            """,
            (
                f"%{role}%",
                f"%{role}%",
                f"%{goal}%",
                f"%{role}%",
            ),
        ).fetchall()

        # Retrieve research findings relevant to the goal.
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
            (
                f"%{goal}%",
                f"%{goal}%",
                f"%{goal}%",
            ),
        ).fetchall()

    return {
        "existing_personas": [dict(row) for row in personas],
        "research_sources": [dict(row) for row in sources],
    }

