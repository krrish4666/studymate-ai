import asyncio
import functools
import json
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

import google.api_core.exceptions
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError
from app.core.security import decrypt_data
from app.models.api_key import ApiKey
from app.models.document_cache import DocumentCache
from app.services.file_parser import file_parser
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)

# Pydantic Schemas for validating (not constraining) AI output
class FlashcardModel(BaseModel):
    id: str
    question: str
    answer: str

    @field_validator("question", "answer")
    @classmethod
    def non_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("flashcard content must be non-empty")
        return v


class FlashcardList(BaseModel):
    flashcards: list[FlashcardModel]


class QuizQuestionModel(BaseModel):
    id: str = ""
    type: str = "mcq"
    question: str
    options: list[str]
    correctAnswer: int
    explanation: str = ""

    @field_validator("question")
    @classmethod
    def question_non_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("quiz question must be non-empty")
        return v

    @field_validator("options")
    @classmethod
    def four_options(cls, v: list[str]) -> list[str]:
        if len(v) != 4 or any(not (o or "").strip() for o in v):
            raise ValueError("quiz options must be exactly 4 non-empty strings")
        return v


class QuizList(BaseModel):
    questions: list[QuizQuestionModel]


class MindMapNodeModel(BaseModel):
    id: str = ""
    label: str
    children: list["MindMapNodeModel"] = []

    @field_validator("label")
    @classmethod
    def label_non_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("mind map nodes must have a non-empty label")
        return v


class MindMapSchema(BaseModel):
    mindmap: MindMapNodeModel


def parse_json_response(raw: str) -> Any:
    """Parse a Gemini text response into JSON, tolerating markdown fences."""
    if not raw or not raw.strip():
        raise BadRequestError("AI returned an empty response")
    text = raw.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip ```json ... ``` fences if the model wrapped the output.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

    raise BadRequestError("AI returned malformed JSON")


def with_retry[**P, R](func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """Bounded exponential backoff retry for Gemini API transient errors."""

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except (
                google.api_core.exceptions.ResourceExhausted,
                google.api_core.exceptions.ServiceUnavailable,
                google.api_core.exceptions.DeadlineExceeded,
            ) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Gemini API failed after {max_retries} attempts: {str(e)}")
                    raise BadRequestError("AI generation temporarily unavailable. Please try again later.") from e
                await asyncio.sleep(2 ** attempt)
            except google.api_core.exceptions.InvalidArgument as e:
                logger.error(f"Gemini API invalid argument: {str(e)}")
                raise BadRequestError("Invalid document content or parameters sent to AI.") from e
            except Exception as e:
                logger.error(f"Unexpected Gemini API error: {str(e)}")
                raise BadRequestError("An unexpected error occurred during AI generation.") from e

    return wrapper


NOTES_SYSTEM_PROMPT = """You are an expert university professor creating comprehensive study notes. Your notes must be detailed, well-structured, and educationally rich.

STRICT FORMAT REQUIREMENTS:
- Start with a clear Title (H1)
- Follow with a short introduction paragraph
- Use numbered sections (1., 2., 3., etc.)
- Within each section use:
  - H3 headings for subsections
  - **bold** for key terms and important concepts
  - *italic* for emphasis and definitions
  - Bullet lists (- ) for points
  - Numbered lists (1. ) for sequences
  - `code` for technical terms, formulas, or commands
  - > blockquotes for important definitions or quotes
  - Tables where comparisons are useful
  - Horizontal rules (---) between major sections

REQUIRED SECTIONS (in order):
1. **Definition** - Simple, clear explanation of the core concept
2. **Core Concepts** - Bullet-pointed key ideas with brief explanations
3. **Detailed Explanation** - Comprehensive breakdown with:
   - Multiple subsections as needed
   - Step-by-step explanations
   - Relationships between concepts
4. **Important Points** - Key facts to remember, prefixed with ✅
5. **Examples** - At least 2-3 practical, real-world examples
6. **Advantages** - Bullet list of benefits
7. **Disadvantages** - Bullet list of limitations
8. **Interview / Exam Questions** - 5-10 practice questions
9. **Summary** - Concise revision summary of key takeaways

QUALITY GUIDELINES:
- Write 1500-3000 words minimum
- Explain concepts as if teaching a beginner
- Include real-world analogies where helpful
- Highlight exam tips with 💡 emoji
- Mark important keywords in **bold**
- Never leave a section empty - if content doesn't apply, note it
- Use markdown tables for comparisons
- End with a horizontal rule and "---" before summary
- Do NOT use excessive summarization - be comprehensive"""

REVISION_SYSTEM_PROMPT = """You are an expert university professor creating a last-minute revision cheat sheet.

Generate a ONE-PAGE summary with these sections:
1. **Key Concepts** - Core ideas in bullet points
2. **Important Formulas** (if applicable) - Use `code` formatting
3. **Mnemonics** - Memory aids to remember concepts
4. **Key Points to Remember** - Critical facts
5. **Common Mistakes to Avoid** - Pitfalls students face
6. **Quick Reference Table** - Comparison of key elements in a markdown table
7. **Frequently Asked Questions** - 3-5 quick Q&A pairs

Format: Clean markdown, max 800 words, 2-column layout friendly.
Use **bold** for emphasis, bullet lists, and a compact scannable style."""

FLASHCARDS_SYSTEM_PROMPT = """You are an expert creating high-quality Anki/Quizlet style flashcards for active recall.

Each flashcard answer must fit in the card without scrolling. STRICT limit: 20-40 words, never exceed 50 words.

Generate 12-18 flashcards following these rules:

ONE CONCEPT — ONE SHORT ANSWER
Each card tests exactly one concept. Answers must be 1-2 short sentences.
If a topic needs more detail, split across multiple cards.

ANSWER GUIDELINES
Prioritize in this order:
- Definition
- Purpose / Key idea
- One short example (only if needed)
Never include: paragraphs, background theory, multiple concepts, repeated information.

GOOD ANSWER EXAMPLES:
"The Observer pattern creates a one-to-many dependency where observers are automatically notified whenever the subject changes state."
"The Mediator pattern centralizes communication between objects, reducing direct dependencies and improving loose coupling."

BAD ANSWER (too long, paragraph style):
"The Observer pattern defines a one-to-many dependency between objects. When one object changes state, all of its dependents are notified and updated automatically while maintaining loose coupling between components..."

QUESTION FORMATS
Test active recall with:
- "What is X?" — definition
- "What problem does X solve?" — purpose
- "What are the benefits of X?" — advantages
- "When would you use X?" — use case
- "How does X differ from Y?" — comparison
- "Give an example of X" — example

NO COPYING
Rewrite in your own words. Never copy from the source material.

Return ONLY valid JSON:
{"flashcards": [{"id": "1", "question": "...", "answer": "..."}]}"""

QUIZ_SYSTEM_PROMPT = """You are an expert university professor creating multiple-choice assessment questions.

STRICT RULES:
- Every question MUST have exactly 4 options (A, B, C, D)
- Every question MUST have exactly one correct answer
- Every question MUST have three plausible distractors
- No True/False, fill-in-blank, or short-answer questions
- All questions must be type "mcq"

Each question must have:
- Clear, unambiguous wording
- Exactly 4 options
- The correct answer index (0-based)
- A brief explanation of why the answer is correct

Return ONLY valid JSON:
{"questions": [{"id": "1", "type": "mcq", "question": "...", "options": ["correct answer", "distractor 1", "distractor 2", "distractor 3"], "correctAnswer": 0, "explanation": "..."}]}"""

MINDMAP_SYSTEM_PROMPT = """You are an expert university professor creating a hierarchical mind map.

Structure requirements:
- Root: The main topic (central concept)
- Level 1: 3-5 major subtopics
- Level 2: 2-4 details per subtopic
- Level 3: (optional) 2-3 specifics per detail
- Max 3 levels deep

Each node must have a short, clear label (max 5 words).

Return ONLY valid JSON:
{"mindmap": {"id": "root", "label": "Central Topic", "children": [{"id": "1", "label": "Subtopic", "children": [{"id": "1.1", "label": "Detail", "children": []}]}]}}"""


class GeminiService:
    DEFAULT_MODEL = "models/gemini-2.5-flash"

    async def get_api_key(self, db: AsyncSession, user_id) -> str:
        result = await db.execute(
            select(ApiKey)
            .where(
                ApiKey.userId == user_id,
                ApiKey.provider == "gemini",
                ApiKey.isActive == True,
            )
            .order_by(ApiKey.createdAt.desc())
            .limit(1)
        )
        api_key = result.scalar_one_or_none()
        if api_key:
            return decrypt_data(api_key.encryptedKey)
        return ""

    def _build_client(self, api_key: str):
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        return genai

    async def _get_cached_text(self, db: AsyncSession, file_record_id) -> str | None:
        result = await db.execute(
            select(DocumentCache).where(DocumentCache.fileRecordId == file_record_id)
        )
        cache = result.scalar_one_or_none()
        if cache:
            return cache.extractedText
        return None

    async def _extract_file_text(self, db: AsyncSession, file_record) -> str:
        cached = await self._get_cached_text(db, file_record.id)
        if cached:
            return cached
        file_data, _ = storage_service.get_stream(file_record.fileUrl)
        text = file_parser.extract_text(file_data.read(), file_record.originalName)
        return text

    async def stream_notes(
        self, db: AsyncSession, user_id, file_record, mode: str, api_key: str, request=None
    ):
        try:
            text_content = await self._extract_file_text(db, file_record)
            genai = self._build_client(api_key)
            model = genai.GenerativeModel(self.DEFAULT_MODEL)

            mode_instruction = (
                "Generate COMPACT notes with bullet points and brief explanations only. Aim for 800-1200 words."
                if mode == "compact"
                else "Generate DETAILED comprehensive notes. Aim for 2000-4000 words."
            )

            prompt = (
                f"{NOTES_SYSTEM_PROMPT}\n\n"
                f"{mode_instruction}\n\n"
                "Generate comprehensive study notes from the following material. "
                "Follow the required format strictly.\n\n"
                f"Material:\n{text_content[:50000]}"
            )

            response = await model.generate_content_async(prompt, stream=True)
            full_text = ""
            async for chunk in response:
                if request and await request.is_disconnected():
                    logger.info("Client disconnected during stream_notes, aborting.")
                    return
                if chunk.text:
                    full_text += chunk.text
                    yield f"data: {json.dumps(chunk.text)}\n\n"

            yield "data: [DONE]\n\n"
            await self._save_output(db, user_id, file_record.id, None, full_text)
        except Exception as e:
            logger.error(f"Error in stream_notes: {str(e)}")
            yield f"data: [ERROR] AI generation failed. Please try again.\n\n"

    async def stream_revision(
        self, db: AsyncSession, user_id, file_record, api_key: str, request=None
    ):
        try:
            text_content = await self._extract_file_text(db, file_record)
            genai = self._build_client(api_key)
            model = genai.GenerativeModel(self.DEFAULT_MODEL)

            prompt = (
                f"{REVISION_SYSTEM_PROMPT}\n\n"
                f"Material:\n{text_content[:50000]}"
            )

            response = await model.generate_content_async(prompt, stream=True)
            full_text = ""
            async for chunk in response:
                if request and await request.is_disconnected():
                    logger.info("Client disconnected during stream_revision, aborting.")
                    return
                if chunk.text:
                    full_text += chunk.text
                    yield f"data: {json.dumps(chunk.text)}\n\n"

            yield "data: [DONE]\n\n"
            await self._save_output(
                db, user_id, file_record.id, None, full_text, feature="revision"
            )
        except Exception as e:
            logger.error(f"Error in stream_revision: {str(e)}")
            yield f"data: [ERROR] AI generation failed. Please try again.\n\n"

    async def _save_output(self, db, user_id, file_record_id, output_json, output_text, feature="notes"):
        from app.models.session_output import SessionOutput

        session_output = SessionOutput(
            fileRecordId=file_record_id,
            userId=user_id,
            feature=feature,
            outputJson=output_json,
            outputText=output_text,
        )
        db.add(session_output)
        await db.flush()

    @with_retry
    async def _call_gemini_json(self, model, prompt: str) -> Any:
        """Call Gemini for an application/json response and parse the JSON."""
        import google.generativeai as genai
        config = genai.GenerationConfig(
            response_mime_type="application/json",
        )
        response = await model.generate_content_async(prompt, generation_config=config)
        return parse_json_response(response.text)

    async def generate_quiz(
        self, db: AsyncSession, user_id, file_record, api_key: str,
        difficulty: str = "medium", count: int = 10,
    ) -> list[dict]:
        text_content = await self._extract_file_text(db, file_record)
        genai = self._build_client(api_key)
        model = genai.GenerativeModel(self.DEFAULT_MODEL)

        prompt = (
            f"{QUIZ_SYSTEM_PROMPT}\n\n"
            f"Generate exactly {count} multiple-choice questions.\n\n"
            f"Difficulty: {difficulty}\n"
            f"Material:\n{text_content[:50000]}"
        )

        result = await self._call_gemini_json(model, prompt)
        if not isinstance(result, dict):
            raise BadRequestError("AI returned an unexpected response shape")

        raw_questions = result.get("questions", [])
        if not isinstance(raw_questions, list):
            raise BadRequestError("AI returned an unexpected response shape")

        questions = []
        for q in raw_questions:
            try:
                validated = QuizQuestionModel.model_validate(q)
            except Exception:
                continue
            # Reject out-of-range correctAnswer references.
            if 0 <= validated.correctAnswer < len(validated.options):
                questions.append(validated.model_dump())

        if not questions:
            raise BadRequestError("AI generation produced no valid quiz questions")

        await self._save_output(
            db, user_id, file_record.id,
            output_json={"questions": questions},
            output_text=None,
            feature="quiz",
        )
        return questions

    async def generate_mindmap(
        self, db: AsyncSession, user_id, file_record, api_key: str,
    ) -> dict:
        text_content = await self._extract_file_text(db, file_record)
        genai = self._build_client(api_key)
        model = genai.GenerativeModel(self.DEFAULT_MODEL)

        prompt = (
            f"{MINDMAP_SYSTEM_PROMPT}\n\n"
            f"Material:\n{text_content[:50000]}"
        )

        result = await self._call_gemini_json(model, prompt)
        if not isinstance(result, dict):
            raise BadRequestError("AI returned an unexpected response shape")

        mindmap = result.get("mindmap", {})
        if not isinstance(mindmap, dict) or not mindmap.get("label"):
            raise BadRequestError("AI generation produced no valid mind map")

        try:
            validated = MindMapSchema.model_validate({"mindmap": mindmap})
        except Exception:
            raise BadRequestError("AI generation produced an invalid mind map")

        mindmap = validated.model_dump()["mindmap"]

        await self._save_output(
            db, user_id, file_record.id,
            output_json={"mindmap": mindmap},
            output_text=None,
            feature="mindmap",
        )
        return mindmap

    async def generate_flashcards(
        self, db: AsyncSession, user_id, file_record, api_key: str
    ) -> list[dict]:
        text_content = await self._extract_file_text(db, file_record)
        genai = self._build_client(api_key)
        model = genai.GenerativeModel(self.DEFAULT_MODEL)

        prompt = (
            f"{FLASHCARDS_SYSTEM_PROMPT}\n\n"
            f"Material:\n{text_content[:50000]}"
        )

        result = await self._call_gemini_json(model, prompt)
        if not isinstance(result, dict):
            raise BadRequestError("AI returned an unexpected response shape")

        raw_flashcards = result.get("flashcards", [])
        if not isinstance(raw_flashcards, list):
            raise BadRequestError("AI returned an unexpected response shape")

        flashcards = []
        for fc in raw_flashcards:
            try:
                cards = FlashcardList.model_validate({"flashcards": [fc]}).model_dump()
                if cards and cards["flashcards"]:
                    flashcards.extend(cards["flashcards"])
            except Exception:
                continue

        if not flashcards:
            raise BadRequestError("AI generation produced no valid flashcards")

        await self._save_output(
            db, user_id, file_record.id,
            output_json={"flashcards": flashcards},
            output_text=None,
            feature="flashcards",
        )
        return flashcards


gemini_service = GeminiService()
