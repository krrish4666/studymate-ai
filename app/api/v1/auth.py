import logging
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import hmac_compare
from app.database import get_db
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    ResetTokenResponse,
    VerifyOtpRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

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
async def google_login(request: Request):
    service = AuthService(None)
    uri, state = await service.google_login_url()
    logger.info(
        "Google OAuth login: request_host=%s location_host=%s redirect_uri=%s "
        "state_generated=%s",
        request.headers.get("host", ""),
        urlsplit(uri).netloc,
        settings.GOOGLE_REDIRECT_URI,
        bool(state),
    )

    redirect_response = RedirectResponse(uri, status_code=302)
    if state:
        redirect_response.set_cookie(
            key=settings.GOOGLE_OAUTH_STATE_COOKIE,
            value=state,
            max_age=600,
            httponly=True,
            samesite="lax",
            path="/",
            secure=False,
        )
        set_cookie = redirect_response.headers.get("set-cookie", "")
        logger.info(
            "Google OAuth login response: status=%s location_present=%s "
            "set_cookie_present=%s cookie_name=%s path=/ domain=absent "
            "secure=False httponly=True samesite=lax max_age=600 expires=absent",
            redirect_response.status_code,
            bool(redirect_response.headers.get("location")),
            settings.GOOGLE_OAUTH_STATE_COOKIE in set_cookie,
            settings.GOOGLE_OAUTH_STATE_COOKIE,
        )

    return redirect_response


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str = Query(None),
    state: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    cookie_header = request.headers.get("cookie", "")
    state_cookie_name = settings.GOOGLE_OAUTH_STATE_COOKIE
    logger.info(
        "Google OAuth callback request: host=%s code_present=%s state_param=%s "
        "cookie_header_present=%s state_cookie_present=%s",
        request.headers.get("host", ""),
        bool(code),
        bool(state),
        bool(cookie_header),
        state_cookie_name in request.cookies,
    )

    if not code:
        raise UnauthorizedError("Missing OAuth code")

    state_expected = request.cookies.get(state_cookie_name, "")
    logger.info(
        "Google OAuth callback state validation: state_cookie_present=%s state_match=%s",
        bool(state_expected),
        state == state_expected if state and state_expected else False,
    )

    if not state or not state_expected:
        logger.error("Google OAuth callback: Missing state parameter or cookie")
        raise UnauthorizedError("Missing OAuth state")

    if not hmac_compare(state, state_expected):
        logger.error("Google OAuth callback: State mismatch")
        raise UnauthorizedError("Invalid OAuth state")

    service = AuthService(db)
    user, token = await service.google_callback(code, state, state_expected)
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
