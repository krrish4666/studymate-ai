import json

import pytest
from pydantic import ValidationError

from app.core.exceptions import BadRequestError
from app.services.gemini_service import (
    FlashcardList,
    FlashcardModel,
    MindMapNodeModel,
    MindMapSchema,
    QuizList,
    QuizQuestionModel,
    parse_json_response,
)


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
