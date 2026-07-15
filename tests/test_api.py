import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.file_record import FileRecord


@pytest.fixture
def mock_file_record() -> MagicMock:
    fr = MagicMock(spec=FileRecord)
    fr.id = uuid.uuid4()
    fr.userId = uuid.uuid4()
    fr.originalName = "test.pdf"
    fr.fileUrl = "/tmp/test.pdf"
    fr.fileType = "pdf"
    fr.fileSize = 1024
    fr.feature = "notes"
    fr.status = "done"
    return fr


@pytest.fixture
async def unauth_client():
    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    async def test_health_check(self, unauth_client: AsyncClient):
        response = await unauth_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"


class TestAuthAPI:
    async def test_register_validation(self, unauth_client: AsyncClient):
        response = await unauth_client.post(
            "/api/v1/auth/register",
            json={"name": "T", "email": "invalid", "password": "123"},
        )
        assert response.status_code == 422

    async def test_register_short_password(self, unauth_client: AsyncClient):
        response = await unauth_client.post(
            "/api/v1/auth/register",
            json={"name": "Test", "email": "test@example.com", "password": "1234567"},
        )
        assert response.status_code == 422

    async def test_login_validation(self, unauth_client: AsyncClient):
        response = await unauth_client.post(
            "/api/v1/auth/login",
            json={"email": "not-an-email", "password": ""},
        )
        assert response.status_code == 422

    async def test_protected_route_without_auth(self, unauth_client: AsyncClient):
        response = await unauth_client.post("/api/v1/upload")
        assert response.status_code == 403 or response.status_code == 422


class TestUploadAPI:
    async def test_upload_no_file(self, client: AsyncClient):
        response = await client.post("/api/v1/upload", data={"feature": "notes"})
        assert response.status_code == 422

    async def test_upload_invalid_feature(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/upload",
            files={"file": ("test.txt", b"hello world", "text/plain")},
            data={"feature": ""},
        )
        assert response.status_code == 422


class TestFeatureAPI:
    async def test_notes_missing_api_key(self, client: AsyncClient, mock_db: MagicMock, mock_file_record: MagicMock):
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_file_record
        with patch("app.api.v1.features.gemini_service.get_api_key", new_callable=AsyncMock) as mock_get_key:
            mock_get_key.return_value = ""

            response = await client.post(
                "/api/v1/features/notes",
                json={"fileRecordId": str(mock_file_record.id), "mode": "detailed"},
            )

        assert response.status_code == 400

    async def test_flashcards_missing_api_key(self, client: AsyncClient, mock_db: MagicMock, mock_file_record: MagicMock):
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_file_record
        with patch("app.api.v1.features.gemini_service.get_api_key", new_callable=AsyncMock) as mock_get_key:
            mock_get_key.return_value = ""

            response = await client.post(
                "/api/v1/features/flashcards",
                json={"fileRecordId": str(mock_file_record.id)},
            )

        assert response.status_code == 400

    async def test_quiz_missing_api_key(self, client: AsyncClient, mock_db: MagicMock, mock_file_record: MagicMock):
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_file_record
        with patch("app.api.v1.features.gemini_service.get_api_key", new_callable=AsyncMock) as mock_get_key:
            mock_get_key.return_value = ""

            response = await client.post(
                "/api/v1/features/quiz",
                json={"fileRecordId": str(mock_file_record.id), "difficulty": "medium", "count": 5},
            )

        assert response.status_code == 400

    async def test_mindmap_missing_api_key(self, client: AsyncClient, mock_db: MagicMock, mock_file_record: MagicMock):
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_file_record
        with patch("app.api.v1.features.gemini_service.get_api_key", new_callable=AsyncMock) as mock_get_key:
            mock_get_key.return_value = ""

            response = await client.post(
                "/api/v1/features/mindmap",
                json={"fileRecordId": str(mock_file_record.id)},
            )

        assert response.status_code == 400

    async def test_revision_missing_api_key(self, client: AsyncClient, mock_db: MagicMock, mock_file_record: MagicMock):
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_file_record
        with patch("app.api.v1.features.gemini_service.get_api_key", new_callable=AsyncMock) as mock_get_key:
            mock_get_key.return_value = ""

            response = await client.post(
                "/api/v1/features/revision",
                json={"fileRecordId": str(mock_file_record.id)},
            )

        assert response.status_code == 400

    async def test_notes_invalid_file_id(self, client: AsyncClient, mock_db: MagicMock):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        response = await client.post(
            "/api/v1/features/notes",
            json={"fileRecordId": "00000000-0000-0000-0000-000000000000", "mode": "detailed"},
        )
        assert response.status_code == 404
