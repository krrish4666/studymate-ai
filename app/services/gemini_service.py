import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import decrypt_data
from app.models.api_key import ApiKey
from app.models.document_cache import DocumentCache
from app.models.file_record import FileRecord
from app.services.file_parser import file_parser
from app.services.storage_service import storage_service


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

FLASHCARDS_SYSTEM_PROMPT = """You are an expert university professor creating flashcards for exam preparation.

Generate 12-18 high-quality flashcards that cover:
- Key definitions
- Important concepts
- Relationships between ideas
- Practical applications
- Common exam questions

Each flashcard must have:
- A clear, specific question on the front
- A concise but complete answer on the back
- Answers should include key terms in **bold**

Return ONLY valid JSON:
{"flashcards": [{"id": "1", "question": "...", "answer": "..."}]}"""

QUIZ_SYSTEM_PROMPT = """You are an expert university professor creating assessment questions.

Generate diverse question types:
- 60% MCQs (4 options, one correct)
- 15% True/False questions
- 15% Fill-in-the-blank questions  
- 10% Short answer questions

Each question must have:
- Clear, unambiguous wording
- 4 options for MCQ, 2 for True/False
- The correct answer index
- A brief explanation of why the answer is correct

Return ONLY valid JSON:
{"questions": [{"id": "1", "type": "mcq", "question": "...", "options": ["A", "B", "C", "D"], "correctAnswer": 0, "explanation": "..."}]}

For True/False: options: ["True", "False"], correctAnswer: 0 or 1
For fill-in-blank: options: ["answer1", "wrong1", "wrong2", "wrong3"], correctAnswer: 0
For short-answer: options: ["expected answer"], correctAnswer: 0"""

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
    DEFAULT_MODEL = "models/gemini-3.1-flash-lite"

    async def get_api_key(self, db: AsyncSession, user_id) -> str:
        result = await db.execute(
            select(ApiKey).where(
                ApiKey.userId == user_id,
                ApiKey.provider == "gemini",
                ApiKey.isActive == True,
            )
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
        self, db: AsyncSession, user_id, file_record, mode: str, api_key: str
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

            response = model.generate_content(prompt, stream=True)
            full_text = ""
            for chunk in response:
                if chunk.text:
                    full_text += chunk.text
                    lines = chunk.text.split("\n")
                    formatted = "\n".join(f"data: {line}" for line in lines)
                    yield f"{formatted}\n\n"

            yield "data: [DONE]\n\n"
            await self._save_output(db, user_id, file_record.id, None, full_text)
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    async def stream_revision(
        self, db: AsyncSession, user_id, file_record, api_key: str
    ):
        try:
            text_content = await self._extract_file_text(db, file_record)
            genai = self._build_client(api_key)
            model = genai.GenerativeModel(self.DEFAULT_MODEL)

            prompt = (
                f"{REVISION_SYSTEM_PROMPT}\n\n"
                f"Material:\n{text_content[:50000]}"
            )

            response = model.generate_content(prompt, stream=True)
            full_text = ""
            for chunk in response:
                if chunk.text:
                    full_text += chunk.text
                    lines = chunk.text.split("\n")
                    formatted = "\n".join(f"data: {line}" for line in lines)
                    yield f"{formatted}\n\n"

            yield "data: [DONE]\n\n"
            await self._save_output(
                db, user_id, file_record.id, None, full_text, feature="revision"
            )
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

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

    async def generate_quiz(
        self, db: AsyncSession, user_id, file_record, api_key: str,
        difficulty: str = "medium", count: int = 10,
    ) -> list[dict]:
        text_content = await self._extract_file_text(db, file_record)
        genai = self._build_client(api_key)
        model = genai.GenerativeModel(self.DEFAULT_MODEL)

        prompt = (
            f"{QUIZ_SYSTEM_PROMPT}\n\n"
            f"Difficulty: {difficulty}\n"
            f"Generate exactly {count} questions.\n\n"
            f"Material:\n{text_content[:50000]}"
        )

        response = model.generate_content(prompt)
        try:
            result = json.loads(response.text.strip())
            questions = result.get("questions", [])
        except (json.JSONDecodeError, AttributeError):
            questions = []

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

        response = model.generate_content(prompt)
        try:
            result = json.loads(response.text.strip())
            mindmap = result.get("mindmap", {})
        except (json.JSONDecodeError, AttributeError):
            mindmap = {"id": "root", "label": "Mind Map", "children": []}

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

        response = model.generate_content(prompt)
        try:
            result = json.loads(response.text.strip())
            flashcards = result.get("flashcards", [])
        except (json.JSONDecodeError, AttributeError):
            flashcards = []

        await self._save_output(
            db, user_id, file_record.id,
            output_json={"flashcards": flashcards},
            output_text=None,
            feature="flashcards",
        )
        return flashcards


gemini_service = GeminiService()
