from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User


@pytest.fixture
async def export_client(mock_db, test_user: User):
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


class TestExportAPI:
    async def test_export_notes_pdf(self, export_client):
        response = await export_client.post(
            "/api/v1/export/pdf",
            json={
                "feature": "notes",
                "outputText": "# Test Notes\nSome content here",
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    async def test_export_flashcards_pdf(self, export_client):
        response = await export_client.post(
            "/api/v1/export/pdf",
            json={
                "feature": "flashcards",
                "outputJson": {
                    "flashcards": [
                        {"id": "1", "question": "Q1", "answer": "A1"},
                    ]
                },
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    async def test_export_quiz_pdf(self, export_client):
        response = await export_client.post(
            "/api/v1/export/pdf",
            json={
                "feature": "quiz",
                "outputJson": {
                    "questions": [
                        {
                            "id": "1",
                            "question": "Test?",
                            "options": ["A", "B", "C", "D"],
                            "correctAnswer": 0,
                        }
                    ]
                },
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    async def test_export_mindmap_pdf(self, export_client):
        response = await export_client.post(
            "/api/v1/export/pdf",
            json={
                "feature": "mindmap",
                "outputJson": {
                    "mindmap": {
                        "id": "root",
                        "label": "Central Topic",
                        "children": [],
                    }
                },
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    async def test_export_revision_pdf(self, export_client):
        response = await export_client.post(
            "/api/v1/export/pdf",
            json={
                "feature": "revision",
                "outputText": "- Key point 1\n- Key point 2",
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    async def test_export_unsupported_feature(self, export_client):
        response = await export_client.post(
            "/api/v1/export/pdf",
            json={"feature": "unknown", "outputText": "test"},
        )
        assert response.status_code == 400
