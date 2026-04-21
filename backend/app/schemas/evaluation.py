import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.evaluation import StatusEnum
from app.services.available_models import AVAILABLE_MODEL_IDS

_MIN_MODEL_COUNT = 2
_MAX_MODEL_COUNT = 5


class ModelResponseOut(BaseModel):
    id: uuid.UUID
    evaluation_id: uuid.UUID
    model_name: str
    response_text: str | None
    run_index: int
    question_version: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EvaluationCreate(BaseModel):
    rubric_id: uuid.UUID
    model_names: list[str] = Field(
        min_length=_MIN_MODEL_COUNT,
        max_length=_MAX_MODEL_COUNT,
    )

    @field_validator("model_names")
    @classmethod
    def validate_model_names(cls, v: list[str]) -> list[str]:
        unknown = set(v) - AVAILABLE_MODEL_IDS
        if unknown:
            raise ValueError(f"Unknown model(s): {unknown}")
        if len(set(v)) != len(v):
            raise ValueError("Duplicate model names are not allowed.")
        if not (_MIN_MODEL_COUNT <= len(v) <= _MAX_MODEL_COUNT):
            raise ValueError(
                f"Between {_MIN_MODEL_COUNT} and {_MAX_MODEL_COUNT} models are required."
            )
        return v


class EvaluationOut(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID | None
    rubric_id: uuid.UUID | None = None
    question: str
    model_names: list[str] | None
    status: StatusEnum
    response_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModelInfoOut(BaseModel):
    id: str
    name: str
    provider: str
