import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.api_key import ApiKey


@pytest.fixture
async def profile_client(mock_db: MagicMock, test_user: User):
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


class TestProfileAPI:
    async def test_get_profile(self, profile_client: AsyncClient, mock_db: MagicMock, test_user: User):
        mock_db.scalar = AsyncMock(return_value=5)

        response = await profile_client.get("/api/v1/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "test@example.com"
        assert data["stats"]["totalFiles"] == 5
        assert data["stats"]["totalSessions"] == 5

    async def test_update_profile(self, profile_client: AsyncClient, mock_db: MagicMock, test_user: User):
        response = await profile_client.patch(
            "/api/v1/profile",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    async def test_list_api_keys_empty(self, profile_client: AsyncClient, mock_db: MagicMock):
        mock_db.execute.return_value.scalars.return_value.all.return_value = []

        response = await profile_client.get("/api/v1/profile/api-keys")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_api_keys_with_items(self, profile_client: AsyncClient, mock_db: MagicMock):
        api_key = MagicMock(spec=ApiKey)
        api_key.id = uuid.uuid4()
        api_key.provider = "gemini"
        api_key.label = "My Key"
        api_key.isActive = True
        api_key.createdAt = datetime.now(timezone.utc)
        mock_db.execute.return_value.scalars.return_value.all.return_value = [api_key]

        response = await profile_client.get("/api/v1/profile/api-keys")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["provider"] == "gemini"

    async def test_create_api_key(self, profile_client: AsyncClient, mock_db: MagicMock):
        with patch("app.api.v1.profile.ApiKey") as mock_api_key_cls:
            mock_key = MagicMock()
            mock_key.id = uuid.uuid4()
            mock_key.provider = "gemini"
            mock_key.label = "My Gemini Key"
            mock_key.isActive = True
            mock_key.createdAt = datetime.now(timezone.utc)
            mock_api_key_cls.return_value = mock_key

            response = await profile_client.post(
                "/api/v1/profile/api-keys",
                json={"provider": "gemini", "key": "test-api-key-12345", "label": "My Gemini Key"},
            )
        assert response.status_code == 201
        data = response.json()
        assert data["provider"] == "gemini"
        assert mock_db.add.called

    async def test_delete_api_key_not_found(self, profile_client: AsyncClient, mock_db: MagicMock):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        response = await profile_client.delete(f"/api/v1/profile/api-keys/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_delete_api_key_success(self, profile_client: AsyncClient, mock_db: MagicMock):
        api_key = MagicMock(spec=ApiKey)
        mock_db.execute.return_value.scalar_one_or_none.return_value = api_key

        response = await profile_client.delete(f"/api/v1/profile/api-keys/{uuid.uuid4()}")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "API key deleted"
