import asyncio
import functools
import hashlib
import json
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

import google.api_core.exceptions
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.exceptions import BadRequestError
from app.core.security import decrypt_data
from app.models.api_key import ApiKey
from app.models.document_cache import DocumentCache
from app.models.session_output import SessionOutput
from app.services.artifact_cache import artifact_cache
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
    ARTIFACT_CONTRACT_VERSION = "v1"

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

    def _artifact_payload(
        self, artifact_type: str, payload: Any
    ) -> dict[str, Any] | None:
        try:
            if artifact_type in {"notes", "revision_sheet"}:
                if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
                    return None
                text = payload["text"].strip()
                return {"text": text} if text else None
            if artifact_type == "flashcards":
                return FlashcardList.model_validate(payload).model_dump()
            if artifact_type == "quiz":
                return QuizList.model_validate(payload).model_dump()
            if artifact_type == "mindmap":
                return MindMapSchema.model_validate(payload).model_dump()
        except Exception:
            return None
        return None

    async def _get_cached_artifact(
        self, key: str, artifact_type: str
    ) -> dict[str, Any] | None:
        cached = await artifact_cache.get(key)
        if cached is None:
            return None
        if (
            cached.get("version") != self.ARTIFACT_CONTRACT_VERSION
            or cached.get("artifact_type") != artifact_type
        ):
            logger.info("Redis artifact cache entry has an old contract version")
            await artifact_cache.delete(key)
            return None
        payload = self._artifact_payload(artifact_type, cached.get("payload"))
        if payload is None:
            logger.warning("Redis artifact cache entry failed schema validation")
            await artifact_cache.delete(key)
            return None
        return payload

    async def _set_cached_artifact(
        self, key: str, artifact_type: str, payload: dict[str, Any]
    ) -> None:
        validated = self._artifact_payload(artifact_type, payload)
        if validated is None:
            return
        await artifact_cache.set(
            key,
            {
                "version": self.ARTIFACT_CONTRACT_VERSION,
                "artifact_type": artifact_type,
                "payload": validated,
            },
        )

    async def _get_reusable_context(
        self, db: AsyncSession, user_id, file_record_id, artifact_type: str
    ) -> tuple[str | None, str | None]:
        preferred_sources = {
            "revision_sheet": ("notes",),
            "flashcards": ("notes", "revision"),
            "quiz": ("notes", "revision"),
            "mindmap": ("notes", "revision"),
        }.get(artifact_type, ())

        for source_feature in preferred_sources:
            result = await db.execute(
                select(SessionOutput)
                .where(
                    SessionOutput.userId == user_id,
                    SessionOutput.fileRecordId == file_record_id,
                    SessionOutput.feature == source_feature,
                )
                .order_by(SessionOutput.createdAt.desc())
                .limit(1)
            )
            output = result.scalar_one_or_none()
            if not output:
                continue
            if output.outputText and output.outputText.strip():
                logger.info("Reusing generated artifact as AI context")
                return source_feature, output.outputText
            if output.outputJson:
                context = json.dumps(output.outputJson, separators=(",", ":"))
                if context:
                    logger.info("Reusing generated artifact as AI context")
                    return source_feature, context
        return None, None

    def _artifact_key(
        self,
        user_id,
        file_record_id,
        artifact_type: str,
        parameters: dict[str, Any],
        source_context: str | None,
    ) -> str:
        source_signature = (
            hashlib.sha256(source_context.encode()).hexdigest()
            if source_context
            else None
        )
        return artifact_cache.build_key(
            user_id,
            file_record_id,
            artifact_type,
            parameters={
                **parameters,
                "contract_version": self.ARTIFACT_CONTRACT_VERSION,
            },
            source_context=source_signature,
            model=self.DEFAULT_MODEL,
        )

    async def _get_cached_text(self, db: AsyncSession, file_record_id) -> str | None:
        result = await db.execute(
            select(DocumentCache).where(DocumentCache.fileRecordId == file_record_id)
        )
        cache = result.scalar_one_or_none()
        if cache and cache.extractedText and cache.extractedText.strip():
            logger.info("Document cache hit for file record")
            return cache.extractedText
        if cache:
            logger.warning("Invalid empty document cache entry; invalidating it")
            await db.delete(cache)
            await db.flush()
        else:
            logger.info("Document cache miss for file record")
        return None

    async def _store_cached_text(
        self, db: AsyncSession, file_record_id, extracted_text: str
    ) -> str:
        if not extracted_text or not extracted_text.strip():
            raise BadRequestError("Document contains no extractable text")

        cache = DocumentCache(
            fileRecordId=file_record_id,
            extractedText=extracted_text,
        )
        try:
            async with db.begin_nested():
                db.add(cache)
                await db.flush()
        except IntegrityError:
            logger.info("Document cache population raced with another request")
            result = await db.execute(
                select(DocumentCache).where(
                    DocumentCache.fileRecordId == file_record_id
                )
            )
            existing_cache = result.scalar_one_or_none()
            if (
                existing_cache
                and existing_cache.extractedText
                and existing_cache.extractedText.strip()
            ):
                logger.info("Using document cache populated by concurrent request")
                return existing_cache.extractedText
            raise
        except SQLAlchemyError:
            logger.exception("Document cache persistence failed")
            raise

        logger.info("Document cache populated for file record")
        return extracted_text

    async def _extract_file_text(self, db: AsyncSession, file_record) -> str:
        cached = await self._get_cached_text(db, file_record.id)
        if cached:
            return cached
        logger.info("Extracting document text after cache miss")
        file_data, _ = storage_service.get_stream(file_record.fileUrl)
        text = file_parser.extract_text(file_data.read(), file_record.originalName)
        return await self._store_cached_text(db, file_record.id, text)

    async def stream_notes(
        self, db: AsyncSession, user_id, file_record, mode: str, api_key: str, request=None
    ):
        try:
            source_feature, source_context = await self._get_reusable_context(
                db, user_id, file_record.id, "notes"
            )
            cache_key = self._artifact_key(
                user_id,
                file_record.id,
                "notes",
                {"mode": mode},
                source_context,
            )
            cached = await self._get_cached_artifact(cache_key, "notes")
            if cached:
                cached_text = cached["text"]
                yield f"data: {json.dumps(cached_text)}\n\n"
                yield "data: [DONE]\n\n"
                await self._save_output(
                    db, user_id, file_record.id, None, cached_text, feature="notes"
                )
                return

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
                f"Material ({source_feature or 'document'}):\n"
                f"{(source_context or text_content)[:50000]}"
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
            await self._set_cached_artifact(
                cache_key, "notes", {"text": full_text}
            )
        except Exception as e:
            logger.error(f"Error in stream_notes: {str(e)}")
            yield f"data: [ERROR] AI generation failed. Please try again.\n\n"

    async def stream_revision(
        self, db: AsyncSession, user_id, file_record, api_key: str, request=None
    ):
        try:
            source_feature, source_context = await self._get_reusable_context(
                db, user_id, file_record.id, "revision_sheet"
            )
            cache_key = self._artifact_key(
                user_id, file_record.id, "revision_sheet", {}, source_context
            )
            cached = await self._get_cached_artifact(cache_key, "revision_sheet")
            if cached:
                cached_text = cached["text"]
                yield f"data: {json.dumps(cached_text)}\n\n"
                yield "data: [DONE]\n\n"
                await self._save_output(
                    db,
                    user_id,
                    file_record.id,
                    None,
                    cached_text,
                    feature="revision",
                )
                return

            text_content = await self._extract_file_text(db, file_record)
            genai = self._build_client(api_key)
            model = genai.GenerativeModel(self.DEFAULT_MODEL)

            prompt = (
                f"{REVISION_SYSTEM_PROMPT}\n\n"
                f"Material ({source_feature or 'document'}):\n"
                f"{(source_context or text_content)[:50000]}"
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
            await self._set_cached_artifact(
                cache_key, "revision_sheet", {"text": full_text}
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
        source_feature, source_context = await self._get_reusable_context(
            db, user_id, file_record.id, "quiz"
        )
        cache_key = self._artifact_key(
            user_id,
            file_record.id,
            "quiz",
            {"difficulty": difficulty, "count": count},
            source_context,
        )
        cached = await self._get_cached_artifact(cache_key, "quiz")
        if cached:
            questions = cached["questions"]
            await self._save_output(
                db, user_id, file_record.id,
                output_json={"questions": questions},
                output_text=None,
                feature="quiz",
            )
            return questions

        text_content = await self._extract_file_text(db, file_record)
        genai = self._build_client(api_key)
        model = genai.GenerativeModel(self.DEFAULT_MODEL)

        prompt = (
            f"{QUIZ_SYSTEM_PROMPT}\n\n"
            f"Generate exactly {count} multiple-choice questions.\n\n"
            f"Difficulty: {difficulty}\n"
            f"Material ({source_feature or 'document'}):\n"
            f"{(source_context or text_content)[:50000]}"
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
        await self._set_cached_artifact(
            cache_key, "quiz", {"questions": questions}
        )
        return questions

    async def generate_mindmap(
        self, db: AsyncSession, user_id, file_record, api_key: str,
    ) -> dict:
        source_feature, source_context = await self._get_reusable_context(
            db, user_id, file_record.id, "mindmap"
        )
        cache_key = self._artifact_key(
            user_id, file_record.id, "mindmap", {}, source_context
        )
        cached = await self._get_cached_artifact(cache_key, "mindmap")
        if cached:
            mindmap = cached["mindmap"]
            await self._save_output(
                db, user_id, file_record.id,
                output_json={"mindmap": mindmap},
                output_text=None,
                feature="mindmap",
            )
            return mindmap

        text_content = await self._extract_file_text(db, file_record)
        genai = self._build_client(api_key)
        model = genai.GenerativeModel(self.DEFAULT_MODEL)

        prompt = (
            f"{MINDMAP_SYSTEM_PROMPT}\n\n"
            f"Material ({source_feature or 'document'}):\n"
            f"{(source_context or text_content)[:50000]}"
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
        await self._set_cached_artifact(
            cache_key, "mindmap", {"mindmap": mindmap}
        )
        return mindmap

    async def generate_flashcards(
        self, db: AsyncSession, user_id, file_record, api_key: str
    ) -> list[dict]:
        source_feature, source_context = await self._get_reusable_context(
            db, user_id, file_record.id, "flashcards"
        )
        cache_key = self._artifact_key(
            user_id, file_record.id, "flashcards", {}, source_context
        )
        cached = await self._get_cached_artifact(cache_key, "flashcards")
        if cached:
            flashcards = cached["flashcards"]
            await self._save_output(
                db, user_id, file_record.id,
                output_json={"flashcards": flashcards},
                output_text=None,
                feature="flashcards",
            )
            return flashcards

        text_content = await self._extract_file_text(db, file_record)
        genai = self._build_client(api_key)
        model = genai.GenerativeModel(self.DEFAULT_MODEL)

        prompt = (
            f"{FLASHCARDS_SYSTEM_PROMPT}\n\n"
            f"Material ({source_feature or 'document'}):\n"
            f"{(source_context or text_content)[:50000]}"
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
        await self._set_cached_artifact(
            cache_key, "flashcards", {"flashcards": flashcards}
        )
        return flashcards


gemini_service = GeminiService()
