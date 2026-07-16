from pathlib import Path

import filetype

from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.file_record import FileRecord
from app.models.document_cache import DocumentCache
from app.schemas.file import FileUploadResponse
from app.core.exceptions import UnsupportedMediaError, TooLargeError
from app.services.storage_service import storage_service
from app.services.file_parser import file_parser
from app.config import settings

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    feature: str = Form("general"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_data = await file.read()

    if len(file_data) > settings.MAX_FILE_SIZE:
        raise TooLargeError("File exceeds 25 MB limit")

    kind = filetype.guess(file_data[:2048])
    mime_type = kind.mime if kind else "application/octet-stream"
    if mime_type not in settings.ALLOWED_FILE_TYPES:
        raise UnsupportedMediaError(f"Unsupported file type: {mime_type}")

    file_url = storage_service.save(file_data, file.filename)

    file_record = FileRecord(
        userId=current_user.id,
        originalName=file.filename,
        fileUrl=file_url,
        fileType=Path(file.filename).suffix.lower().lstrip("."),
        fileSize=len(file_data),
        feature=feature,
        status="done",
    )
    db.add(file_record)
    await db.flush()
    await db.refresh(file_record)

    try:
        extracted_text = file_parser.extract_text(file_data, file.filename)
        cache = DocumentCache(
            fileRecordId=file_record.id,
            extractedText=extracted_text,
        )
        db.add(cache)
        await db.flush()
    except Exception:
        pass

    return FileUploadResponse(
        fileRecordId=str(file_record.id),
        fileUrl=file_url,
        fileType=file_record.fileType,
        originalName=file_record.originalName,
        fileSize=file_record.fileSize,
    )
