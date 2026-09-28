import json
import io
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import BadRequestError
from app.models.document_cache import DocumentCache
from app.services.file_parser import file_parser
from app.services.gemini_service import (
    FlashcardList,
    FlashcardModel,
    MindMapNodeModel,
    MindMapSchema,
    QuizList,
    QuizQuestionModel,
    parse_json_response,
)
from app.services.gemini_service import gemini_service
from app.services.storage_service import storage_service


class _NestedTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


class _CacheDb:
    def __init__(self, caches=None, raise_integrity_once=False):
        self.caches = dict(caches or {})
        self.pending = None
        self.raise_integrity_once = raise_integrity_once
        self.add_calls = 0
        self.delete_calls = 0

    async def execute(self, _statement):
        cache = self.caches.get(next(iter(self.caches), None))
        return SimpleNamespace(scalar_one_or_none=lambda: cache)

    def add(self, cache):
        self.add_calls += 1
        self.pending = cache

    async def flush(self):
        if self.pending is None:
            return
        if self.raise_integrity_once:
            self.raise_integrity_once = False
            raise IntegrityError("insert", {}, Exception("duplicate key"))
        self.caches[self.pending.fileRecordId] = self.pending
        self.pending = None

    async def delete(self, cache):
        self.delete_calls += 1
        self.caches.pop(cache.fileRecordId, None)

    def begin_nested(self):
        return _NestedTransaction()


def _file_record(file_id=None):
    record = MagicMock()
    record.id = file_id or uuid.uuid4()
    record.fileUrl = "uploads/document.txt"
    record.originalName = "document.txt"
    return record


class TestDocumentCache:
    @pytest.mark.asyncio
    async def test_cache_hit_does_not_parse(self):
        file_record = _file_record()
        db = _CacheDb(
            {file_record.id: DocumentCache(
                fileRecordId=file_record.id,
                extractedText="cached text",
            )}
        )

        with patch.object(file_parser, "extract_text") as extract_text:
            assert await gemini_service._extract_file_text(db, file_record) == "cached text"

        extract_text.assert_not_called()
        assert db.add_calls == 0

    @pytest.mark.asyncio
    async def test_cache_miss_parses_and_writes_back(self):
        file_record = _file_record()
        db = _CacheDb()

        with (
            patch.object(storage_service, "get_stream", return_value=(io.BytesIO(b"raw"), None)),
            patch.object(file_parser, "extract_text", return_value="parsed text") as extract_text,
        ):
            result = await gemini_service._extract_file_text(db, file_record)

        assert result == "parsed text"
        extract_text.assert_called_once_with(b"raw", "document.txt")
        assert db.caches[file_record.id].extractedText == "parsed text"

    @pytest.mark.asyncio
    async def test_subsequent_request_reuses_cache(self):
        file_record = _file_record()
        db = _CacheDb()

        with (
            patch.object(storage_service, "get_stream", return_value=(io.BytesIO(b"raw"), None)),
            patch.object(file_parser, "extract_text", return_value="parsed text") as extract_text,
        ):
            await gemini_service._extract_file_text(db, file_record)
            extract_text.reset_mock()
            result = await gemini_service._extract_file_text(db, file_record)

        assert result == "parsed text"
        extract_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_cache_is_invalidated_and_reparsed(self):
        file_record = _file_record()
        db = _CacheDb(
            {file_record.id: DocumentCache(
                fileRecordId=file_record.id,
                extractedText="   ",
            )}
        )

        with (
            patch.object(storage_service, "get_stream", return_value=(io.BytesIO(b"raw"), None)),
            patch.object(file_parser, "extract_text", return_value="recovered text"),
        ):
            result = await gemini_service._extract_file_text(db, file_record)

        assert result == "recovered text"
        assert db.delete_calls == 1
        assert db.caches[file_record.id].extractedText == "recovered text"

    @pytest.mark.asyncio
    async def test_empty_parsed_document_is_rejected(self):
        file_record = _file_record()
        db = _CacheDb()

        with (
            patch.object(storage_service, "get_stream", return_value=(io.BytesIO(b"raw"), None)),
            patch.object(file_parser, "extract_text", return_value=""),
            pytest.raises(BadRequestError, match="no extractable text"),
        ):
            await gemini_service._extract_file_text(db, file_record)

    @pytest.mark.asyncio
    async def test_concurrent_cache_population_uses_existing_row(self):
        file_record = _file_record()
        existing = DocumentCache(
            fileRecordId=file_record.id,
            extractedText="winner text",
        )
        db = _CacheDb({file_record.id: existing}, raise_integrity_once=True)

        assert (
            await gemini_service._store_cached_text(db, file_record.id, "loser text")
            == "winner text"
        )
        assert len(db.caches) == 1
        assert db.caches[file_record.id].extractedText == "winner text"

    def test_cache_key_is_unique_and_foreign_key_cascades(self):
        column = DocumentCache.__table__.c.fileRecordId
        assert column.primary_key
        assert any(
            fk.ondelete == "CASCADE" and fk.target_fullname == "file_records.id"
            for fk in column.foreign_keys
        )

    @pytest.mark.asyncio
    async def test_different_documents_have_independent_cache_entries(self):
        first_id = uuid.uuid4()
        second_id = uuid.uuid4()
        db = _CacheDb()

        await gemini_service._store_cached_text(db, first_id, "first")
        await gemini_service._store_cached_text(db, second_id, "second")

        assert len(db.caches) == 2
        assert db.caches[first_id].extractedText == "first"
        assert db.caches[second_id].extractedText == "second"


class TestParseJsonResponse:
    def test_plain_json(self) -> None:
        assert parse_json_response('{"a": 1}') == {"a": 1}

    def test_markdown_fenced_json(self) -> None:
        raw = "```json\n{\"a\": 1}\n```"
        assert parse_json_response(raw) == {"a": 1}

    def test_fenced_json_without_language(self) -> None:
        raw = "```\n{\"flashcards\": []}\n```"
        assert parse_json_response(raw) == {"flashcards": []}

    def test_empty_response_raises(self) -> None:
        with pytest.raises(BadRequestError, match="empty response"):
            parse_json_response("")

    def test_malformed_raises(self) -> None:
        with pytest.raises(BadRequestError, match="malformed JSON"):
            parse_json_response("not json at all")


class TestQuizValidation:
    def test_valid_question(self) -> None:
        q = QuizQuestionModel(
            id="1",
            type="mcq",
            question="What is X?",
            options=["A", "B", "C", "D"],
            correctAnswer=0,
            explanation="Because",
        )
        assert q.correctAnswer == 0

    def test_rejects_less_than_four_options(self) -> None:
        with pytest.raises(ValidationError):
            QuizQuestionModel(
                id="1",
                type="mcq",
                question="Q",
                options=["A", "B"],
                correctAnswer=0,
                explanation="",
            )

    def test_rejects_more_than_four_options(self) -> None:
        with pytest.raises(ValidationError):
            QuizQuestionModel(
                id="1",
                type="mcq",
                question="Q",
                options=["A", "B", "C", "D", "E"],
                correctAnswer=0,
                explanation="",
            )

    def test_rejects_empty_option(self) -> None:
        with pytest.raises(ValidationError):
            QuizQuestionModel(
                id="1",
                type="mcq",
                question="Q",
                options=["A", "", "C", "D"],
                correctAnswer=0,
                explanation="",
            )


class TestFlashcardValidation:
    def test_valid_flashcard(self) -> None:
        fc = FlashcardModel(id="1", question="Q", answer="A")
        assert fc.question == "Q"

    def test_rejects_empty_answer(self) -> None:
        with pytest.raises(ValidationError):
            FlashcardModel(id="1", question="Q", answer="   ")


class TestMindMapValidation:
    def test_recursive_nodes(self) -> None:
        node = MindMapNodeModel(
            id="root",
            label="Topic",
            children=[
                MindMapNodeModel(id="1", label="A", children=[]),
                MindMapNodeModel(
                    id="2",
                    label="B",
                    children=[MindMapNodeModel(id="2.1", label="B1", children=[])],
                ),
            ],
        )
        assert len(node.children) == 2
        assert node.children[1].children[0].label == "B1"

    def test_rejects_empty_label(self) -> None:
        with pytest.raises(ValidationError):
            MindMapSchema.model_validate(
                {"mindmap": {"id": "root", "label": "", "children": []}}
            )


class TestGenerationModelsList:
    def test_quiz_list_parses(self) -> None:
        data = {
            "questions": [
                {
                    "id": "1",
                    "type": "mcq",
                    "question": "Q?",
                    "options": ["A", "B", "C", "D"],
                    "correctAnswer": 1,
                    "explanation": "E",
                }
            ]
        }
        parsed = QuizList.model_validate(data)
        assert len(parsed.questions) == 1

    def test_flashcard_list_parses(self) -> None:
        data = {"flashcards": [{"id": "1", "question": "Q", "answer": "A"}]}
        parsed = FlashcardList.model_validate(data)
        assert len(parsed.flashcards) == 1

    def test_parse_json_roundtrip(self) -> None:
        payload = {"questions": []}
        out = parse_json_response(json.dumps(payload))
        assert out == payload
