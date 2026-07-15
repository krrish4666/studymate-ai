from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.file_record import FileRecord
from app.schemas.feature import NotesRequest, FlashcardResponse, Flashcard, QuizRequest, QuizQuestionResponse, QuizQuestion, MindMapResponse, MindMapNode
from app.core.exceptions import NotFoundError, BadRequestError
from app.services.gemini_service import gemini_service

router = APIRouter(prefix="/features", tags=["Features"])


async def _resolve_file_record(
    file_record_id: str, user_id, db: AsyncSession
) -> FileRecord:
    result = await db.execute(
        select(FileRecord).where(
            FileRecord.id == file_record_id,
            FileRecord.userId == user_id,
        )
    )
    file_record = result.scalar_one_or_none()
    if not file_record:
        raise NotFoundError("File record not found")
    return file_record


async def _resolve_api_key(db: AsyncSession, user_id) -> str:
    api_key = await gemini_service.get_api_key(db, user_id)
    if not api_key:
        raise BadRequestError(
            "No Gemini API key found. Add one in your profile settings."
        )
    return api_key


@router.post("/notes")
async def generate_notes(
    body: NotesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = await _resolve_file_record(body.fileRecordId, current_user.id, db)
    api_key = await _resolve_api_key(db, current_user.id)

    return StreamingResponse(
        gemini_service.stream_notes(
            db, current_user.id, file_record, body.mode, api_key
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/flashcards", response_model=FlashcardResponse)
async def generate_flashcards(
    body: NotesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = await _resolve_file_record(body.fileRecordId, current_user.id, db)
    api_key = await _resolve_api_key(db, current_user.id)

    flashcards = await gemini_service.generate_flashcards(
        db, current_user.id, file_record, api_key
    )

    return FlashcardResponse(
        flashcards=[Flashcard(**fc) for fc in flashcards]
    )


@router.post("/quiz", response_model=QuizQuestionResponse)
async def generate_quiz(
    body: QuizRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = await _resolve_file_record(body.fileRecordId, current_user.id, db)
    api_key = await _resolve_api_key(db, current_user.id)

    questions = await gemini_service.generate_quiz(
        db, current_user.id, file_record, api_key,
        difficulty=body.difficulty, count=body.count,
    )

    return QuizQuestionResponse(
        questions=[QuizQuestion(**q) for q in questions]
    )


@router.post("/mindmap", response_model=MindMapResponse)
async def generate_mindmap(
    body: NotesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = await _resolve_file_record(body.fileRecordId, current_user.id, db)
    api_key = await _resolve_api_key(db, current_user.id)

    mindmap = await gemini_service.generate_mindmap(
        db, current_user.id, file_record, api_key,
    )

    return MindMapResponse(mindmap=MindMapNode(**mindmap))


@router.post("/revision")
async def generate_revision(
    body: NotesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = await _resolve_file_record(body.fileRecordId, current_user.id, db)
    api_key = await _resolve_api_key(db, current_user.id)

    return StreamingResponse(
        gemini_service.stream_revision(
            db, current_user.id, file_record, api_key
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
