import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.artifact_cache import ArtifactCache, artifact_cache
from app.services.gemini_service import gemini_service


class FakeRedis:
    def __init__(self, value=None):
        self.value = value
        self.set_calls = []

    async def get(self, key):
        return self.value

    async def set(self, key, value, ex):
        self.set_calls.append((key, json.loads(value), ex))

    async def delete(self, key):
        self.value = None


@pytest.mark.asyncio
async def test_redis_disabled_is_a_noop():
    cache = ArtifactCache()
    with patch("app.services.artifact_cache.settings.REDIS_ENABLED", False):
        assert await cache.get("key") is None
        await cache.set("key", {"payload": "value"})


@pytest.mark.asyncio
async def test_redis_unavailable_is_best_effort():
    cache = ArtifactCache()
    with (
        patch("app.services.artifact_cache.settings.REDIS_ENABLED", True),
        patch.object(cache, "_get_client", side_effect=ConnectionError("offline")),
    ):
        assert await cache.get("key") is None
        await cache.set("key", {"payload": "value"})


@pytest.mark.asyncio
async def test_cache_hit_returns_validated_artifact_without_gemini():
    db = MagicMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None))
    file_record = MagicMock(id=uuid.uuid4())
    cached = {"flashcards": [{"id": "1", "question": "Q", "answer": "A"}]}
    with (
        patch.object(gemini_service, "_get_cached_artifact", AsyncMock(return_value=cached)),
        patch.object(gemini_service, "_extract_file_text", AsyncMock()) as extract_text,
        patch.object(gemini_service, "_build_client") as build_client,
        patch.object(gemini_service, "_save_output", AsyncMock()),
    ):
        result = await gemini_service.generate_flashcards(db, uuid.uuid4(), file_record, "api-key")

    assert result == cached["flashcards"]
    extract_text.assert_not_called()
    build_client.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_cached_artifact_is_deleted():
    artifact_cache._client = FakeRedis(
        json.dumps(
            {
                "version": "v1",
                "artifact_type": "quiz",
                "payload": {"questions": [{"not": "valid"}]},
            }
        )
    )
    with patch("app.services.artifact_cache.settings.REDIS_ENABLED", True):
        value = await gemini_service._get_cached_artifact("key", "quiz")

    assert value is None
    assert artifact_cache._client.value is None


def test_cache_key_isolated_by_user_document_artifact_and_version():
    cache = ArtifactCache()
    key = cache.build_key("user-1", "file-1", "quiz", {"count": 10})

    assert key.startswith("studymate:artifact:user-1:file-1:quiz:v1:")
    assert key != cache.build_key("user-2", "file-1", "quiz", {"count": 10})
    assert key != cache.build_key("user-1", "file-2", "quiz", {"count": 10})
    assert key != cache.build_key("user-1", "file-1", "flashcards", {"count": 10})
    assert key != cache.build_key("user-1", "file-1", "quiz", {"count": 5})


@pytest.mark.asyncio
async def test_successful_artifact_is_serialized_with_ttl():
    cache = ArtifactCache()
    client = FakeRedis()
    cache._client = client
    with (
        patch("app.services.artifact_cache.settings.REDIS_ENABLED", True),
        patch("app.services.artifact_cache.settings.REDIS_ARTIFACT_TTL_SECONDS", 60),
    ):
        await cache.set("key", {"payload": {"questions": []}})

    assert client.set_calls == [
        (
            "key",
            {"payload": {"questions": []}},
            60,
        )
    ]


@pytest.mark.asyncio
async def test_notes_are_reused_for_downstream_artifacts():
    output = MagicMock()
    output.outputText = "Existing notes"
    output.outputJson = None
    db = MagicMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: output))

    source, context = await gemini_service._get_reusable_context(
        db, uuid.uuid4(), uuid.uuid4(), "quiz"
    )

    assert source == "notes"
    assert context == "Existing notes"


@pytest.mark.asyncio
async def test_revision_is_reused_when_notes_are_unavailable():
    revision = MagicMock()
    revision.outputText = "Revision sheet"
    revision.outputJson = None
    result = SimpleNamespace(scalar_one_or_none=lambda: revision)
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            SimpleNamespace(scalar_one_or_none=lambda: None),
            result,
        ]
    )

    source, context = await gemini_service._get_reusable_context(
        db, uuid.uuid4(), uuid.uuid4(), "mindmap"
    )

    assert source == "revision"
    assert context == "Revision sheet"


@pytest.mark.asyncio
async def test_failed_generation_does_not_write_artifact_cache():
    db = MagicMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None))
    file_record = MagicMock(id=uuid.uuid4())
    with (
        patch.object(gemini_service, "_extract_file_text", AsyncMock(return_value="text")),
        patch.object(gemini_service, "_build_client", return_value=MagicMock()),
        patch.object(
            gemini_service,
            "_call_gemini_json",
            AsyncMock(side_effect=RuntimeError("generation failed")),
        ),
        patch.object(gemini_service, "_set_cached_artifact", AsyncMock()) as set_cache,
    ):
        with pytest.raises(RuntimeError):
            await gemini_service.generate_quiz(db, uuid.uuid4(), file_record, "api-key")

    set_cache.assert_not_awaited()
