from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.export import ExportPdfRequest
from app.core.exceptions import BadRequestError
from app.services.pdf_service import pdf_service

router = APIRouter(prefix="/export", tags=["Export"])


@router.post("/pdf")
async def export_pdf(
    body: ExportPdfRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.feature == "notes":
        pdf_buf = pdf_service.generate_notes_pdf(body.outputText or "")
    elif body.feature == "revision":
        pdf_buf = pdf_service.generate_revision_pdf(body.outputText or "")
    elif body.feature == "flashcards":
        data = body.outputJson or {}
        pdf_buf = pdf_service.generate_flashcards_pdf(data.get("flashcards", []))
    elif body.feature == "quiz":
        data = body.outputJson or {}
        pdf_buf = pdf_service.generate_quiz_pdf(data.get("questions", []))
    elif body.feature == "mindmap":
        data = body.outputJson or {}
        pdf_buf = pdf_service.generate_mindmap_pdf(data.get("mindmap", {}))
    else:
        raise BadRequestError(f"Unsupported feature: {body.feature}")

    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{body.feature}_export.pdf"',
        },
    )
