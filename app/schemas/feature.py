from pydantic import BaseModel


class NotesRequest(BaseModel):
    fileRecordId: str
    mode: str = "detailed"


class Flashcard(BaseModel):
    id: str
    question: str
    answer: str


class FlashcardResponse(BaseModel):
    flashcards: list[Flashcard]


class QuizRequest(BaseModel):
    fileRecordId: str
    difficulty: str = "medium"
    count: int = 10


class QuizQuestion(BaseModel):
    id: str
    question: str
    options: list[str]
    correctAnswer: int


class QuizQuestionResponse(BaseModel):
    questions: list[QuizQuestion]


class MindMapNode(BaseModel):
    id: str
    label: str
    children: list["MindMapNode"] = []


class MindMapResponse(BaseModel):
    mindmap: MindMapNode


class RevisionRequest(BaseModel):
    fileRecordId: str
