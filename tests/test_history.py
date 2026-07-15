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
from app.models.session_output import SessionOutput


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
    fr.errorMessage = None
    fr.createdAt = datetime.now(timezone.utc)
    return fr


@pytest.fixture
def mock_session_output() -> MagicMock:
    so = MagicMock(spec=SessionOutput)
    so.id = uuid.uuid4()
    so.feature = "notes"
    so.outputJson = None
    so.outputText = "# Notes\n\nSome content here"
    so.pdfUrl = None
    so.createdAt = datetime.now(timezone.utc)
    return so


@pytest.fixture
async def history_client(mock_db: MagicMock, test_user: User):
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


class TestHistoryAPI:
    async def test_list_history_empty(self, history_client: AsyncClient, mock_db: MagicMock):
        mock_db.execute.return_value.scalars.return_value.all.return_value = []

        response = await history_client.get("/api/v1/history")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_history_with_items(self, history_client: AsyncClient, mock_db: MagicMock, mock_file_record: MagicMock):
        mock_db.execute.return_value.scalars.return_value.all.return_value = [mock_file_record]

        response = await history_client.get("/api/v1/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["originalName"] == "test.pdf"

    async def test_list_history_filtered(self, history_client: AsyncClient, mock_db: MagicMock, mock_file_record: MagicMock):
        mock_db.execute.return_value.scalars.return_value.all.return_value = [mock_file_record]

        response = await history_client.get("/api/v1/history?feature=notes")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    async def test_get_history_detail_not_found(self, history_client: AsyncClient, mock_db: MagicMock):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        response = await history_client.get(f"/api/v1/history/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_get_history_detail_with_output(
        self, history_client: AsyncClient, mock_db: MagicMock,
        mock_file_record: MagicMock, mock_session_output: MagicMock,
    ):
        mock_file_record.session_outputs = [mock_session_output]
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_file_record

        response = await history_client.get(f"/api/v1/history/{mock_file_record.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["fileRecord"]["originalName"] == "test.pdf"
        assert data["output"]["feature"] == "notes"

    async def test_delete_history_not_found(self, history_client: AsyncClient, mock_db: MagicMock):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        response = await history_client.delete(f"/api/v1/history/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_delete_history_success(self, history_client: AsyncClient, mock_db: MagicMock, mock_file_record: MagicMock):
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_file_record

        response = await history_client.delete(f"/api/v1/history/{mock_file_record.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Session deleted"

    async def test_download_file_not_found(self, history_client: AsyncClient, mock_db: MagicMock):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        response = await history_client.get(f"/api/v1/history/{uuid.uuid4()}/file")
        assert response.status_code == 404

    async def test_download_file_success(
        self, history_client: AsyncClient, mock_db: MagicMock, mock_file_record: MagicMock,
    ):
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_file_record
        with patch("app.api.v1.history.storage_service.get_stream") as mock_stream:
            import io
            mock_stream.return_value = (io.BytesIO(b"test content"), "application/pdf")
            response = await history_client.get(f"/api/v1/history/{mock_file_record.id}/file")
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/pdf"

    async def test_download_pdf_not_found(self, history_client: AsyncClient, mock_db: MagicMock):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        response = await history_client.get(f"/api/v1/history/{uuid.uuid4()}/pdf")
        assert response.status_code == 404

    async def test_download_pdf_success(
        self, history_client: AsyncClient, mock_db: MagicMock,
        mock_file_record: MagicMock, mock_session_output: MagicMock,
    ):
        mock_file_record.session_outputs = [mock_session_output]
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_file_record

        response = await history_client.get(f"/api/v1/history/{mock_file_record.id}/pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
