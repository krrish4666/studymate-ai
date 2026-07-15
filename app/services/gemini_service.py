from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import decrypt_data
from app.models.api_key import ApiKey
from app.services.file_parser import file_parser
from app.services.storage_service import storage_service


class GeminiService:
    DEFAULT_MODEL = "models/gemini-2.0-flash"

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

    async def _extract_file_text(self, file_record) -> str:
        file_data, _ = storage_service.get_stream(file_record.fileUrl)
        return file_parser.extract_text(file_data.read(), file_record.originalName)

    async def stream_notes(
        self, db: AsyncSession, user_id, file_record, mode: str, api_key: str
    ):
        text_content = await self._extract_file_text(file_record)
        genai = self._build_client(api_key)
        model = genai.GenerativeModel(self.DEFAULT_MODEL)

        mode_instruction = (
            "Provide a brief, compact summary with bullet points only."
            if mode == "compact"
            else "Provide comprehensive, detailed, well-structured markdown notes with headings, subheadings, and explanations."
        )

        prompt = (
            "You are an expert academic tutor. Convert the following study material into structured notes.\n"
            f"{mode_instruction}\n\n"
            "Format your response in clean Markdown.\n\n"
            f"Material:\n{text_content[:50000]}"
        )

        response = model.generate_content(prompt, stream=True)
        full_text = ""
        for chunk in response:
            if chunk.text:
                full_text += chunk.text
                yield f"data: {chunk.text}\n\n"

        yield f"data: [DONE]\n\n"
        await self._save_output(db, user_id, file_record.id, None, full_text)

    async def stream_revision(
        self, db: AsyncSession, user_id, file_record, api_key: str
    ):
        text_content = await self._extract_file_text(file_record)
        genai = self._build_client(api_key)
        model = genai.GenerativeModel(self.DEFAULT_MODEL)

        prompt = (
            "You are an expert academic tutor. Create a concise revision cheat sheet "
            "from the following study material.\n"
            "Strictly limit your response to a maximum of 600 words.\n"
            "Use bullet points, short phrases, and key formulas/concepts only. "
            "Format for quick scanning in a 2-column layout.\n\n"
            f"Material:\n{text_content[:50000]}"
        )

        response = model.generate_content(prompt, stream=True)
        full_text = ""
        for chunk in response:
            if chunk.text:
                full_text += chunk.text
                yield f"data: {chunk.text}\n\n"

        yield f"data: [DONE]\n\n"
        await self._save_output(
            db, user_id, file_record.id, None, full_text, feature="revision"
        )

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
        text_content = await self._extract_file_text(file_record)
        genai = self._build_client(api_key)
        model = genai.GenerativeModel(self.DEFAULT_MODEL)

        prompt = (
            f"You are an expert academic tutor. Create a {difficulty} difficulty MCQ quiz "
            f"with exactly {count} questions from the following study material.\n"
            "Each question must have exactly 4 options with one correct answer.\n"
            "Return ONLY valid JSON in this exact format (no markdown, no code fences):\n"
            '{"questions": [{"id": "1", "question": "...", "options": ["A", "B", "C", "D"], "correctAnswer": 0}]}\n'
            "correctAnswer is the 0-based index of the correct option.\n\n"
            f"Material:\n{text_content[:50000]}"
        )

        response = model.generate_content(prompt)
        import json
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
        text_content = await self._extract_file_text(file_record)
        genai = self._build_client(api_key)
        model = genai.GenerativeModel(self.DEFAULT_MODEL)

        prompt = (
            "You are an expert academic tutor. Create a hierarchical mind map "
            "from the following study material.\n"
            "The mind map must have a central root topic with up to 3 levels of depth.\n"
            "Return ONLY valid JSON in this exact format (no markdown, no code fences):\n"
            '{"mindmap": {"id": "root", "label": "Central Topic", '
            '"children": [{"id": "1", "label": "Subtopic", '
            '"children": [{"id": "1.1", "label": "Detail", "children": []}]}]}}\n\n'
            f"Material:\n{text_content[:50000]}"
        )

        response = model.generate_content(prompt)
        import json
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
        text_content = await self._extract_file_text(file_record)
        genai = self._build_client(api_key)
        model = genai.GenerativeModel(self.DEFAULT_MODEL)

        prompt = (
            "You are an expert academic tutor. Create a set of flashcards from the following study material.\n"
            "Generate 10-15 flashcards that cover the key concepts.\n"
            "Return ONLY valid JSON in this exact format (no markdown, no code fences):\n"
            '{"flashcards": [{"id": "1", "question": "...", "answer": "..."}]}\n\n'
            f"Material:\n{text_content[:50000]}"
        )

        response = model.generate_content(prompt)
        import json
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
