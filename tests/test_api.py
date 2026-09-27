import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
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
    async def test_google_login_emits_state_cookie(self, unauth_client: AsyncClient):
        with patch(
            "app.api.v1.auth.AuthService.google_login_url",
            new=AsyncMock(
                return_value=(
                    "https://accounts.google.com/o/oauth2/v2/auth?state=opaque-state",
                    "opaque-state",
                )
            ),
        ):
            response = await unauth_client.get(
                "/api/v1/auth/google/login",
                follow_redirects=False,
            )

        assert response.status_code == 302
        assert response.headers["location"].startswith("https://accounts.google.com/")
        assert response.cookies.get("studymate_oauth_state") == "opaque-state"
        set_cookie = response.headers["set-cookie"]
        assert "studymate_oauth_state=opaque-state" in set_cookie
        assert "Max-Age=600" in set_cookie
        assert "Path=/" in set_cookie
        assert "SameSite=lax" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Secure" not in set_cookie

    async def test_google_login_response_has_expected_host_and_redirect(
        self, unauth_client: AsyncClient
    ):
        with patch(
            "app.api.v1.auth.AuthService.google_login_url",
            new=AsyncMock(
                return_value=(
                    "https://accounts.google.com/o/oauth2/v2/auth"
                    "?redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fv1%2Fauth%2Fgoogle%2Fcallback"
                    "&state=opaque-state",
                    "opaque-state",
                )
            ),
        ):
            response = await unauth_client.get(
                "/api/v1/auth/google/login",
                follow_redirects=False,
            )

        assert response.request.url.host == "test"
        assert "localhost%3A8000%2Fapi%2Fv1%2Fauth%2Fgoogle%2Fcallback" in (
            response.headers["location"]
        )

    async def test_google_callback_accepts_cookie_state(
        self, client: AsyncClient, mock_db: MagicMock
    ):
        with patch(
            "app.api.v1.auth.AuthService.google_login_url",
            new=AsyncMock(
                return_value=(
                    "https://accounts.google.com/o/oauth2/v2/auth?state=opaque-state",
                    "opaque-state",
                )
            ),
        ):
            login_response = await client.get(
                "/api/v1/auth/google/login",
                follow_redirects=False,
            )

        assert login_response.cookies.get("studymate_oauth_state") == "opaque-state"

        with patch(
            "app.api.v1.auth.AuthService.google_callback",
            new=AsyncMock(return_value=(MagicMock(), "jwt-token")),
        ) as google_callback:
            callback_response = await client.get(
                "/api/v1/auth/google/callback",
                params={"code": "authorization-code", "state": "opaque-state"},
                follow_redirects=False,
            )

        assert callback_response.status_code == 307
        assert callback_response.headers["location"] == (
            "http://localhost:8000/login?token=jwt-token"
        )
        google_callback.assert_awaited_once_with(
            "authorization-code", "opaque-state", "opaque-state"
        )

    async def test_google_callback_missing_state_cookie_returns_401(
        self, unauth_client: AsyncClient
    ):
        response = await unauth_client.get(
            "/api/v1/auth/google/callback",
            params={"code": "authorization-code", "state": "opaque-state"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Missing OAuth state"

    async def test_google_callback_mismatched_state_returns_401(
        self, unauth_client: AsyncClient
    ):
        unauth_client.cookies.set("studymate_oauth_state", "stored-state")

        response = await unauth_client.get(
            "/api/v1/auth/google/callback",
            params={"code": "authorization-code", "state": "query-state"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid OAuth state"

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
        assert response.status_code == 401


class TestUploadAPI:
    async def test_upload_no_file(self, client: AsyncClient):
        response = await client.post("/api/v1/upload", data={"feature": "notes"})
        assert response.status_code == 422

    async def test_upload_unsupported_file(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/upload",
            files={"file": ("test.xyz", b"not a real file", "application/x-unknown")},
            data={"feature": "notes"},
        )
        assert response.status_code == 415

    async def test_upload_empty_non_text(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/upload",
            files={"file": ("empty.bin", b"", "application/octet-stream")},
            data={"feature": "notes"},
        )
        assert response.status_code == 415

    async def test_upload_empty_txt_returns_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/upload",
            files={"file": ("empty.txt", b"", "text/plain")},
            data={"feature": "notes"},
        )
        assert response.status_code == 200


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
