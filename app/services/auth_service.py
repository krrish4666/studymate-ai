import uuid
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    encrypt_data,
    decrypt_data,
)
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from app.models.user import User, Account, VerificationToken
from app.services.email_service import email_service


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, name: str, email: str, password: str) -> tuple[User, str]:
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise ConflictError("Email already registered")

        user = User(
            name=name,
            email=email,
            passwordHash=hash_password(password),
        )
        self.db.add(user)
        await self.db.flush()

        account = Account(
            userId=user.id,
            type="credentials",
            provider="credentials",
            providerAccountId=email,
        )
        self.db.add(account)
        await self.db.flush()

        token = create_access_token(user.id)
        return user, token

    async def login(self, email: str, password: str) -> tuple[User, str]:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not user.passwordHash:
            raise UnauthorizedError("Invalid email or password")
        if not verify_password(password, user.passwordHash):
            raise UnauthorizedError("Invalid email or password")

        token = create_access_token(user.id)
        return user, token

    async def google_login_url(self) -> str:
        from authlib.integrations.httpx_client import OAuth2Client

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "scope": "openid email profile",
            "response_type": "code",
            "access_type": "offline",
        }
        client = OAuth2Client(client_id=settings.GOOGLE_CLIENT_ID)
        uri, _ = client.create_authorization_url(
            "https://accounts.google.com/o/oauth2/v2/auth",
            **params,
        )
        return uri

    async def google_callback(self, code: str) -> tuple[User, str]:
        from httpx import AsyncClient

        async with AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            token_data = token_response.json()
            if "error" in token_data:
                raise UnauthorizedError("Google OAuth failed")

            access_token_google = token_data.get("access_token")
            userinfo_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token_google}"},
            )
            userinfo = userinfo_response.json()

        google_id = str(userinfo["id"])
        email = userinfo["email"]
        name = userinfo.get("name", "")
        picture = userinfo.get("picture", "")

        result = await self.db.execute(
            select(Account).where(
                Account.provider == "google",
                Account.providerAccountId == google_id,
            )
        )
        existing_account = result.scalar_one_or_none()

        if existing_account:
            user_result = await self.db.execute(
                select(User).where(User.id == existing_account.userId)
            )
            user = user_result.scalar_one()
        else:
            existing_user_result = await self.db.execute(
                select(User).where(User.email == email)
            )
            existing_user = existing_user_result.scalar_one_or_none()

            if existing_user:
                account = Account(
                    userId=existing_user.id,
                    type="oauth",
                    provider="google",
                    providerAccountId=google_id,
                )
                self.db.add(account)
                user = existing_user
            else:
                user = User(
                    name=name,
                    email=email,
                    image=picture,
                    emailVerified=datetime.now(timezone.utc),
                )
                self.db.add(user)
                await self.db.flush()

                account = Account(
                    userId=user.id,
                    type="oauth",
                    provider="google",
                    providerAccountId=google_id,
                )
                self.db.add(account)

        await self.db.flush()
        token = create_access_token(user.id)
        return user, token

    async def forgot_password(self, email: str) -> str:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("No account with this email")

        otp = "".join(secrets.choice("0123456789") for _ in range(6))
        expires = datetime.now(timezone.utc) + timedelta(minutes=15)

        vt = VerificationToken(
            identifier=email,
            token=otp,
            expires=expires,
        )
        self.db.add(vt)
        await self.db.flush()

        await email_service.send_otp(email, otp)
        return otp

    async def verify_otp(self, email: str, otp: str) -> str:
        result = await self.db.execute(
            select(VerificationToken).where(
                VerificationToken.identifier == email,
                VerificationToken.token == otp,
            )
        )
        vt = result.scalar_one_or_none()
        if not vt:
            raise BadRequestError("Invalid OTP")
        if vt.expires < datetime.now(timezone.utc):
            raise BadRequestError("OTP expired")

        reset_data = f"{email}:{datetime.now(timezone.utc).isoformat()}"
        reset_token = encrypt_data(reset_data)

        await self.db.delete(vt)
        await self.db.flush()

        return reset_token

    async def reset_password(self, reset_token: str, new_password: str) -> None:
        try:
            decrypted = decrypt_data(reset_token)
            email, timestamp_str = decrypted.split(":", 1)
            timestamp = datetime.fromisoformat(timestamp_str)
            if datetime.now(timezone.utc) - timestamp > timedelta(minutes=15):
                raise BadRequestError("Reset token expired")
        except BadRequestError:
            raise
        except Exception:
            raise BadRequestError("Invalid reset token")

        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User not found")

        user.passwordHash = hash_password(new_password)
        await self.db.flush()
