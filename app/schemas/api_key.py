import uuid
from datetime import datetime

from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    provider: str
    key: str
    label: str | None = None


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    provider: str
    label: str | None = None
    isActive: bool
    createdAt: datetime

    model_config = {"from_attributes": True}
