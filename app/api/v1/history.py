import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.file_record import FileRecord
from app.models.session_output import SessionOutput
from app.schemas.history import HistoryItemResponse, HistoryDetailResponse, FileRecordDetail, SessionOutputDetail
from app.core.exceptions import NotFoundError
from app.services.storage_service import storage_service
from app.services.pdf_service import pdf_service

router = APIRouter(prefix="/history", tags=["History"])


@router.get("", response_model=list[HistoryItemResponse])
async def list_history(
    feature: str | None = Query(None, description="Filter by feature type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(FileRecord).where(
        FileRecord.userId == current_user.id
    ).order_by(FileRecord.createdAt.desc())

    if feature:
        stmt = stmt.where(FileRecord.feature == feature)

    result = await db.execute(stmt)
    records = result.scalars().all()
    return [HistoryItemResponse.model_validate(r) for r in records]


@router.get("/{record_id}", response_model=HistoryDetailResponse)
async def get_history_detail(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FileRecord)
        .where(FileRecord.id == record_id, FileRecord.userId == current_user.id)
        .options(selectinload(FileRecord.session_outputs))
    )
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise NotFoundError("Session not found")

    output = None
    if file_record.session_outputs:
        output = file_record.session_outputs[0]

    return HistoryDetailResponse(
        fileRecord=FileRecordDetail.model_validate(file_record),
        output=SessionOutputDetail.model_validate(output) if output else None,
    )


@router.delete("/{record_id}")
async def delete_history(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FileRecord).where(
            FileRecord.id == record_id,
            FileRecord.userId == current_user.id,
        )
    )
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise NotFoundError("Session not found")

    await db.execute(
        delete(SessionOutput).where(SessionOutput.fileRecordId == record_id)
    )
    await db.delete(file_record)
    return {"message": "Session deleted"}


@router.get("/{record_id}/file")
async def download_file(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FileRecord).where(
            FileRecord.id == record_id,
            FileRecord.userId == current_user.id,
        )
    )
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise NotFoundError("Session not found")

    stream, content_type = storage_service.get_stream(file_record.fileUrl)

    return StreamingResponse(
        stream,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{file_record.originalName}"',
        },
    )


@router.get("/{record_id}/pdf")
async def download_history_pdf(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FileRecord)
        .where(FileRecord.id == record_id, FileRecord.userId == current_user.id)
        .options(selectinload(FileRecord.session_outputs))
    )
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise NotFoundError("Session not found")

    output = file_record.session_outputs[0] if file_record.session_outputs else None
    if not output:
        raise NotFoundError("No output found for this session")

    feature = output.feature
    pdf_buf = None

    if feature == "notes":
        pdf_buf = pdf_service.generate_notes_pdf(
            output.outputText or "",
            title=f"Notes - {file_record.originalName}",
        )
    elif feature == "revision":
        pdf_buf = pdf_service.generate_revision_pdf(
            output.outputText or "",
            title=f"Revision - {file_record.originalName}",
        )
    elif feature == "flashcards":
        data = output.outputJson or {}
        pdf_buf = pdf_service.generate_flashcards_pdf(
            data.get("flashcards", []),
            title=f"Flashcards - {file_record.originalName}",
        )
    elif feature == "quiz":
        data = output.outputJson or {}
        pdf_buf = pdf_service.generate_quiz_pdf(
            data.get("questions", []),
            title=f"Quiz - {file_record.originalName}",
        )
    elif feature == "mindmap":
        data = output.outputJson or {}
        pdf_buf = pdf_service.generate_mindmap_pdf(
            data.get("mindmap", {}),
            title=f"Mind Map - {file_record.originalName}",
        )
    else:
        raise NotFoundError(f"Unknown feature type: {feature}")

    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{file_record.originalName}_{feature}.pdf"',
        },
    )
