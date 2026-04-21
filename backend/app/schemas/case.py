import uuid
from datetime import datetime

from pydantic import BaseModel


class CaseCreate(BaseModel):
    title: str
    filename: str
    raw_text: str | None = None


class CaseOut(BaseModel):
    id: uuid.UUID
    title: str
    filename: str
    raw_text: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
