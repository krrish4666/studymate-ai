import uuid
import secrets
import logging
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
    hmac_compare,
)
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from app.models.user import User, Account, VerificationToken
from app.services.email_service import email_service

logger = logging.getLogger(__name__)


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

        token = create_access_token(
            user.id,
            name=user.name,
            email=user.email,
            image=user.image,
        )
        return user, token

    async def login(self, email: str, password: str) -> tuple[User, str]:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not user.passwordHash:
            raise UnauthorizedError("Invalid email or password")
        if not verify_password(password, user.passwordHash):
            raise UnauthorizedError("Invalid email or password")

        token = create_access_token(
            user.id,
            name=user.name,
            email=user.email,
            image=user.image,
        )
        return user, token

    async def google_login_url(self) -> tuple[str, str]:
        from authlib.integrations.httpx_client import OAuth2Client

        client = OAuth2Client(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )
        # Authlib generates state and stores it internally for this request
        uri, state = client.create_authorization_url(
            url="https://accounts.google.com/o/oauth2/v2/auth",
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
            scope="openid email profile",
            access_type="offline",
        )
        return uri, state

    async def google_callback(self, code: str, state_from_client: str, state_expected: str) -> tuple[User, str]:
        logger.info(f"Google OAuth callback: checking state (provided={bool(state_from_client)}, expected={bool(state_expected)})")
        
        if not state_expected or not state_from_client:
            logger.error("Google OAuth: Missing state parameters")
            raise UnauthorizedError("Invalid OAuth state")
            
        if not hmac_compare(state_from_client, state_expected):
            logger.error("Google OAuth: State mismatch")
            raise UnauthorizedError("Invalid OAuth state")

        logger.info("Google OAuth: State validated successfully")
        import httpx
        from httpx import AsyncClient

        try:
            logger.info("Google OAuth: Exchanging code for token...")
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
                    timeout=10.0,
                )
                
                # Log HTTP status for debugging
                logger.info(f"Google OAuth: Token exchange HTTP status: {token_response.status_code}")
                
                token_response.raise_for_status()
                token_data = token_response.json()
                
                if "error" in token_data:
                    logger.error(f"Google OAuth token error: {token_data.get('error')}")
                    raise UnauthorizedError("Google OAuth failed: " + token_data.get("error_description", "Unknown error"))

                access_token_google = token_data.get("access_token")
                if not access_token_google:
                    logger.error("Google OAuth: Missing access token in response")
                    raise UnauthorizedError("Google OAuth failed: Missing access token")

                logger.info("Google OAuth: Fetching userinfo...")
                userinfo_response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token_google}"},
                    timeout=10.0,
                )
                
                logger.info(f"Google OAuth: Userinfo HTTP status: {userinfo_response.status_code}")
                
                userinfo_response.raise_for_status()
                userinfo = userinfo_response.json()
                logger.info(f"Google OAuth: Got userinfo for {userinfo.get('email')}")

        except httpx.RequestError as e:
            logger.error(f"Google OAuth network error: {type(e).__name__}: {str(e)}")
            raise UnauthorizedError(f"Network error during Google OAuth: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Google OAuth HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            raise UnauthorizedError(f"Google OAuth provider returned error status: {e.response.status_code}")
        except ValueError as e:
            logger.error(f"Google OAuth: Invalid JSON response: {str(e)}")
            raise UnauthorizedError("Invalid JSON response from Google OAuth provider")

        google_id = str(userinfo.get("id"))
        if not google_id or google_id == "None":
            raise UnauthorizedError("Google OAuth failed: Missing user ID")
            
        email = userinfo.get("email")
        if not email:
            raise UnauthorizedError("Google OAuth failed: Missing email")
            
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
            logger.info("Google OAuth: Existing account found")
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
                logger.info("Google OAuth: Linking to existing user by email")
                account = Account(
                    userId=existing_user.id,
                    type="oauth",
                    provider="google",
                    providerAccountId=google_id,
                )
                self.db.add(account)
                user = existing_user
            else:
                logger.info("Google OAuth: Creating new user")
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

        if picture:
            user.image = picture
        if name and not user.name:
            user.name = name

        await self.db.flush()
        token = create_access_token(
            user.id,
            name=user.name,
            email=user.email,
            image=user.image,
        )
        logger.info("Google OAuth: Success - JWT created")
        return user, token

    async def forgot_password(self, email: str) -> str:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            # Do not reveal whether the account exists.
            # Return a generic success message without creating any OTP.
            return ""

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
