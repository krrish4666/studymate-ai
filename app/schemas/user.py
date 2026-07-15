import uuid
from datetime import datetime

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str | None = None
    email: str
    image: str | None = None
    emailVerified: datetime | None = None
    createdAt: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: str | None = None
    image: str | None = None


class UserStats(BaseModel):
    totalFiles: int = 0
    totalSessions: int = 0


class UserProfileResponse(BaseModel):
    user: UserResponse
    stats: UserStats
