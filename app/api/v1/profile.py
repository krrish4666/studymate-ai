import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.file_record import FileRecord
from app.models.session_output import SessionOutput
from app.models.api_key import ApiKey
from app.schemas.user import UserResponse, UserUpdate, UserProfileResponse, UserStats
from app.schemas.api_key import ApiKeyCreate, ApiKeyResponse
from app.core.security import encrypt_data, decrypt_data
from app.core.exceptions import NotFoundError, BadRequestError

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("", response_model=UserProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_count = await db.scalar(
        select(func.count(FileRecord.id)).where(FileRecord.userId == current_user.id)
    )
    session_count = await db.scalar(
        select(func.count(SessionOutput.id)).where(SessionOutput.userId == current_user.id)
    )

    return UserProfileResponse(
        user=UserResponse.model_validate(current_user),
        stats=UserStats(
            totalFiles=file_count or 0,
            totalSessions=session_count or 0,
        ),
    )


@router.patch("", response_model=UserResponse)
async def update_profile(
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.name is not None:
        current_user.name = body.name
    if body.image is not None:
        current_user.image = body.image

    await db.flush()
    return UserResponse.model_validate(current_user)


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ApiKey).where(ApiKey.userId == current_user.id).order_by(ApiKey.createdAt.desc())
    )
    keys = result.scalars().all()
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.post("/api-keys", response_model=ApiKeyResponse, status_code=201)
async def create_api_key(
    body: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    encrypted = encrypt_data(body.key)
    api_key = ApiKey(
        userId=current_user.id,
        provider=body.provider,
        encryptedKey=encrypted,
        label=body.label,
    )
    db.add(api_key)
    await db.flush()
    return ApiKeyResponse.model_validate(api_key)


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.userId == current_user.id,
        )
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise NotFoundError("API key not found")

    await db.delete(api_key)
    return {"message": "API key deleted"}
