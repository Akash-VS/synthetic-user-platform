
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from app.database.repository import archive_persona
from app.database.repository import archive_persona

from app.database.repository import update_persona

from app.services.persona_service import create_persona
from app.database.repository import list_personas, get_persona
from app.database.repository import restore_persona

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware



from app.services.trait_generator import (
    generate_psychological_profile,
)
from app.services.interview_service import (
    generate_interview_response,
)
from app.services.survey_service import (
    SurveyQuestion,
    generate_survey_response,
)

from app.database.module2_repository import (
    initialize_module2_tables,
    get_persona_memories,
    save_persona_memory,
    get_profile,
)

from typing import Literal

from app.services.consistency_service import (
    validate_persona_consistency,
)

from app.database.module2_repository import (
    get_latest_consistency_report,
)



app = FastAPI(
    title="Synthetic User Generation Platform",
    description="Generate and manage synthetic user personas for Figma usability research.",
    version="1.0.0",
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PersonaRequest(BaseModel):
    role: str = Field(min_length=2, max_length=100)
    experience: str = Field(min_length=2, max_length=50)
    goal: str = Field(min_length=5, max_length=500)


@app.get("/")
def home():
    return {"message": "Synthetic User Generation Platform API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/api/personas/generate")
def generate(request: PersonaRequest):
    try:
        persona = create_persona(
            role=request.role,
            experience=request.experience,
            goal=request.goal,
        )
        return persona.model_dump()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Persona generation failed: {exc}",
        ) from exc


@app.get("/api/personas")
def get_personas(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return {
        "items": list_personas(limit=limit, offset=offset),
        "limit": limit,
        "offset": offset,
    }


@app.get("/api/personas/{persona_id}")
def get_persona_by_id(persona_id: int):
    persona = get_persona(persona_id)

    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")

    return persona


@app.patch("/api/personas/{persona_id}/archive")
def archive_persona_endpoint(persona_id: int):
    if not archive_persona(persona_id):
        raise HTTPException(
            status_code=404,
            detail="Active persona not found",
        )

    return {
        "message": "Persona archived successfully",
        "persona_id": persona_id,
    }
    


from typing import Optional


class PersonaUpdate(BaseModel):
    role: Optional[str] = Field(default=None, min_length=2, max_length=100)
    experience_level: Optional[str] = Field(default=None, min_length=2, max_length=50)
    skills: Optional[list[str]] = None
    goals: Optional[list[str]] = None
    preferences: Optional[list[str]] = None
    challenges: Optional[list[str]] = None
    working_style: Optional[str] = Field(default=None, min_length=2, max_length=500)


@app.patch("/api/personas/{persona_id}")
def edit_persona(persona_id: int, request: PersonaUpdate):
    updates = request.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one field to update",
        )

    if not update_persona(persona_id, updates):
        raise HTTPException(
            status_code=404,
            detail="Active persona not found",
        )

    return get_persona(persona_id)

@app.patch("/api/personas/{persona_id}/restore")
def restore_archived_persona(persona_id: int):
    restored = restore_persona(persona_id)

    if not restored:
        raise HTTPException(
            status_code=404,
            detail="Archived persona not found",
        )

    return {
        "message": "Persona restored successfully",
        "persona_id": persona_id,
        "persona_status": "active",
    }
    
    
    
from pydantic import BaseModel, Field


class InterviewRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class SurveyRequest(BaseModel):
    questions: list[SurveyQuestion] = Field(
        min_length=1,
        max_length=30,
    )


@app.on_event("startup")
def initialize_module2():
    initialize_module2_tables()


@app.post("/api/personas/{persona_id}/psychological-profile")
def create_psychological_profile(persona_id: int):
    try:
        return generate_psychological_profile(persona_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Profile generation failed: {exc}",
        ) from exc


@app.post("/api/personas/{persona_id}/interview")
def create_interview_response(
    persona_id: int,
    request: InterviewRequest,
):
    try:
        generated_response = generate_interview_response(
            persona_id,
            request.question,
        )

        validation = validate_generated_response(
            persona_id=persona_id,
            response_data=generated_response,
            response_type="interview",
        )

        return {
            "response": generated_response,
            "consistency": validation,
        }

    except ValueError as exc:
        status = 404 if str(exc) == "Persona not found" else 400
        raise HTTPException(
            status_code=status,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Interview generation failed: {exc}",
        ) from exc


@app.post("/api/personas/{persona_id}/survey")
def create_survey_response(
    persona_id: int,
    request: SurveyRequest,
):
    try:
        generated_response = generate_survey_response(
            persona_id,
            request.questions,
        )

        validation = validate_generated_response(
            persona_id=persona_id,
            response_data=generated_response,
            response_type="survey",
        )

        return {
            "response": generated_response,
            "consistency": validation,
        }

    except ValueError as exc:
        status = 404 if str(exc) == "Persona not found" else 400
        raise HTTPException(
            status_code=status,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Survey generation failed: {exc}",
        ) from exc



class PersonaMemoryRequest(BaseModel):
    memory_type: str = Field(min_length=2, max_length=50)
    content: str = Field(min_length=1, max_length=5000)
    source_id: Optional[int] = Field(default=None, ge=1)


@app.get("/api/personas/{persona_id}/memories")
def list_persona_memories(
    persona_id: int,
    limit: int = Query(default=20, ge=1, le=200),
):
    persona = get_persona(persona_id)
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")

    memories = get_persona_memories(persona_id, limit=limit)

    return {
        "persona_id": persona_id,
        "count": len(memories),
        "memories": memories,
    }


@app.post("/api/personas/{persona_id}/memories")
def create_persona_memory(
    persona_id: int,
    request: PersonaMemoryRequest,
):
    persona = get_persona(persona_id)
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")

    memory_id = save_persona_memory(
        persona_id=persona_id,
        memory_type=request.memory_type,
        content=request.content,
        source_id=request.source_id,
    )

    return {
        "message": "Persona memory saved successfully",
        "persona_id": persona_id,
        "memory_id": memory_id,
    }
    
    
    

class ConsistencyRequest(BaseModel):
    response: str = Field(min_length=3, max_length=5000)
    response_type: Literal["interview", "survey", "general"] = "general"


@app.post("/api/personas/{persona_id}/validate-consistency")
def validate_consistency_endpoint(
    persona_id: int,
    request: ConsistencyRequest,
):
    persona = get_persona(persona_id)

    if persona is None:
        raise HTTPException(
            status_code=404,
            detail="Persona not found",
        )

    try:
        report = validate_persona_consistency(
            persona_id=persona_id,
            new_response=request.response,
            response_type=request.response_type,
        )

        return {
            "message": "Consistency validation completed",
            "report": report,
        }

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


@app.get("/api/personas/{persona_id}/validation-report")
def get_validation_report_endpoint(persona_id: int):
    persona = get_persona(persona_id)

    if persona is None:
        raise HTTPException(
            status_code=404,
            detail="Persona not found",
        )

    saved_report = get_latest_consistency_report(persona_id)

    if saved_report is None:
        raise HTTPException(
            status_code=404,
            detail="No validation report exists for this persona yet",
        )

    return saved_report


def validate_generated_response(
    persona_id: int,
    response_data,
    response_type: str,
):
    # Convert the existing service result into text for validation.
    if isinstance(response_data, str):
        response_text = response_data
    elif hasattr(response_data, "model_dump"):
        response_text = response_data.model_dump_json()
    elif isinstance(response_data, dict):
        import json
        response_text = json.dumps(response_data, ensure_ascii=False)
    else:
        response_text = str(response_data)

    try:
        report = validate_persona_consistency(
            persona_id=persona_id,
            new_response=response_text,
            response_type=response_type,
        )
    except Exception as exc:
        # Do not lose a successfully generated response if validation fails.
        return {
            "status": "validation_failed",
            "error": str(exc),
            "report": None,
        }

    return {
        "status": report["overall_status"],
        "consistency_score": report["consistency_score"],
        "report": report,
    }
