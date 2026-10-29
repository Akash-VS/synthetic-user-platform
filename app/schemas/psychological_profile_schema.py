from typing import Literal

from pydantic import BaseModel, Field


class PsychologicalProfile(BaseModel):
    persona_id: int

    guidance_preference: int = Field(ge=0, le=100)
    openness_to_new_tools: int = Field(ge=0, le=100)
    risk_tolerance: int = Field(ge=0, le=100)
    confidence_level: int = Field(ge=0, le=100)
    patience_level: int = Field(ge=0, le=100)

    decision_style: Literal[
        "analytical",
        "experimental",
        "guidance_seeking",
        "intuitive",
    ]

    explanation: str = Field(min_length=10, max_length=1000)