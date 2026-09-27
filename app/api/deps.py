import uuid

from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedError
from app.models.user import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    auth: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not auth or not auth.credentials:
        raise UnauthorizedError("Missing or invalid authorization header")

    token = auth.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedError("Invalid or expired token")

    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Token missing user identifier")

    try:
        parsed_uuid = uuid.UUID(user_id)
    except ValueError:
        raise UnauthorizedError("Invalid user identifier format")

    result = await db.execute(select(User).where(User.id == parsed_uuid))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedError("User not found")

    return user
