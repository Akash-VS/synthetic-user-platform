
import pytest
from fastapi.testclient import TestClient

from app import main
from app.database import connection, repository
from app.services.persona_generator import Persona


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Use an isolated database for every test.
    monkeypatch.setattr(
        connection,
        "DATABASE_PATH",
        tmp_path / "test_personas.db",
    )

    def make_persona(role):
        return Persona(
            role=role,
            experience_level="Intermediate",
            skills=["Prototyping", "User Testing"],
            goals=["Improve Figma usability"],
            preferences=["Simple interface"],
            challenges=["Complex prototype flows"],
            working_style="Collaborative",
        )

    repository.save_persona(make_persona("UX Designer"))
    repository.save_persona(make_persona("Frontend Developer"))
    connection.initialize_database()

    with TestClient(main.app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_list_personas(client):
    response = client.get("/api/personas")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


def test_get_existing_persona(client):
    response = client.get("/api/personas/1")
    assert response.status_code == 200
    assert response.json()["role"] == "UX Designer"


def test_missing_persona_returns_404(client):
    response = client.get("/api/personas/999")
    assert response.status_code == 404


def test_update_active_persona(client):
    response = client.patch(
        "/api/personas/1",
        json={
            "goals": ["Evaluate accessibility"],
            "working_style": "Collaborative and iterative",
        },
    )

    assert response.status_code == 200
    assert "Evaluate accessibility" in response.json()["goals"]
    assert response.json()["working_style"] == (
        "Collaborative and iterative"
    )


def test_archive_persona(client):
    response = client.patch("/api/personas/2/archive")
    assert response.status_code == 200

    stored = repository.get_persona(2)
    assert stored["persona_status"] == "archived"


def test_archived_persona_cannot_be_updated(client):
    client.patch("/api/personas/2/archive")

    response = client.patch(
        "/api/personas/2",
        json={"working_style": "Updated style"},
    )

    assert response.status_code == 404


def test_generate_persona_without_calling_gemini(
    client, monkeypatch
):
    persona = Persona(
        role="UX Researcher",
        experience_level="Intermediate",
        skills=["Research"],
        goals=["Evaluate Figma usability"],
        preferences=["Clear workflows"],
        challenges=["Finding usability issues"],
        working_style="Analytical",
    )

    def fake_create_persona(role, experience, goal):
        repository.save_persona(persona)
        return persona

    monkeypatch.setattr(
        main,
        "create_persona",
        fake_create_persona,
    )

    response = client.post(
        "/api/personas/generate",
        json={
            "role": "UX Researcher",
            "experience": "Intermediate",
            "goal": "Evaluate Figma usability",
        },
    )

    assert response.status_code == 200
    assert response.json()["role"] == "UX Researcher"
    assert len(client.get("/api/personas").json()["items"]) == 3
