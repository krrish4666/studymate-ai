import uuid
from datetime import datetime

from pydantic import BaseModel


class HistoryFilter(BaseModel):
    feature: str | None = None


class HistoryItemResponse(BaseModel):
    id: uuid.UUID
    originalName: str
    fileType: str
    feature: str
    status: str
    createdAt: datetime

    model_config = {"from_attributes": True}


class HistoryDetailResponse(BaseModel):
    fileRecord: "FileRecordDetail"
    output: "SessionOutputDetail | None" = None


class FileRecordDetail(BaseModel):
    id: uuid.UUID
    originalName: str
    fileUrl: str
    fileType: str
    fileSize: int | None = None
    feature: str
    status: str
    errorMessage: str | None = None
    createdAt: datetime

    model_config = {"from_attributes": True}


class SessionOutputDetail(BaseModel):
    id: uuid.UUID
    feature: str
    outputJson: dict | None = None
    outputText: str | None = None
    pdfUrl: str | None = None
    createdAt: datetime

    model_config = {"from_attributes": True}
