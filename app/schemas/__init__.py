from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    ForgotPasswordRequest,
    VerifyOtpRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse, UserUpdate, UserProfileResponse
from app.schemas.api_key import ApiKeyCreate, ApiKeyResponse
from app.schemas.file import FileUploadResponse
from app.schemas.feature import (
    NotesRequest,
    FlashcardResponse,
    QuizRequest,
    QuizQuestionResponse,
    MindMapResponse,
    RevisionRequest,
    MindMapNode,
    Flashcard,
    QuizQuestion,
)
from app.schemas.history import (
    HistoryItemResponse,
    HistoryDetailResponse,
    HistoryFilter,
)
from app.schemas.export import ExportPdfRequest

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "LoginResponse",
    "ForgotPasswordRequest",
    "VerifyOtpRequest",
    "ResetPasswordRequest",
    "TokenResponse",
    "UserResponse",
    "UserUpdate",
    "UserProfileResponse",
    "ApiKeyCreate",
    "ApiKeyResponse",
    "FileUploadResponse",
    "NotesRequest",
    "FlashcardResponse",
    "QuizRequest",
    "QuizQuestionResponse",
    "MindMapResponse",
    "RevisionRequest",
    "MindMapNode",
    "Flashcard",
    "QuizQuestion",
    "HistoryItemResponse",
    "HistoryDetailResponse",
    "HistoryFilter",
    "ExportPdfRequest",
]
