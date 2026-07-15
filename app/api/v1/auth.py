from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    ForgotPasswordRequest,
    VerifyOtpRequest,
    ResetPasswordRequest,
    MessageResponse,
    ResetTokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=LoginResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user, token = await service.register(body.name, body.email, body.password)
    return LoginResponse(
        user=UserResponse.model_validate(user),
        access_token=token,
    )


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user, token = await service.login(body.email, body.password)
    return LoginResponse(
        user=UserResponse.model_validate(user),
        access_token=token,
    )


@router.get("/google/login")
async def google_login():
    service = AuthService(None)
    uri = await service.google_login_url()
    return RedirectResponse(uri)


@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user, token = await service.google_callback(code)
    redirect_url = f"{settings.FRONTEND_URL}/login?token={token}"
    return RedirectResponse(redirect_url)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    await service.forgot_password(body.email)
    return MessageResponse(message="If an account exists, an OTP has been sent")


@router.post("/verify-otp", response_model=ResetTokenResponse)
async def verify_otp(body: VerifyOtpRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    reset_token = await service.verify_otp(body.email, body.otp)
    return ResetTokenResponse(resetToken=reset_token)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    await service.reset_password(body.resetToken, body.newPassword)
    return MessageResponse(message="Password reset successfully")
