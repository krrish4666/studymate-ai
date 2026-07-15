import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import app as _app
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User


@pytest.fixture
def test_user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def test_user(test_user_id: uuid.UUID) -> User:
    user = MagicMock(spec=User)
    user.id = test_user_id
    user.name = "Test User"
    user.email = "test@example.com"
    user.image = None
    user.emailVerified = datetime.now(timezone.utc)
    user.createdAt = datetime.now(timezone.utc)
    user.updatedAt = datetime.now(timezone.utc)
    return user


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_result.scalars = MagicMock()
    db.execute = AsyncMock(return_value=mock_result)
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = MagicMock()
    db.commit = MagicMock()
    db.rollback = MagicMock()
    db.close = MagicMock()
    return db


@pytest.fixture
def app() -> FastAPI:
    return _app


@pytest.fixture
async def client(app: FastAPI, mock_db: MagicMock, test_user: User) -> AsyncClient:
    async def _override_db():
        yield mock_db

    async def _override_user():
        return test_user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    from app.core.security import create_access_token
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}
