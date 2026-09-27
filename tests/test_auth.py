import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.services.auth_service import AuthService
from app.core.exceptions import ConflictError, UnauthorizedError, BadRequestError
from app.models.user import User


@pytest.fixture
def auth_service(mock_db: AsyncMock) -> AuthService:
    return AuthService(mock_db)


class TestRegister:
    async def test_register_success(self, auth_service: AuthService, mock_db: AsyncMock):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        user, token = await auth_service.register("Test", "test@example.com", "securePass123")

        assert user.name == "Test"
        assert user.email == "test@example.com"
        assert user.passwordHash is not None
        assert user.passwordHash != "securePass123"
        assert token is not None
        assert mock_db.add.called

    async def test_register_duplicate_email(self, auth_service: AuthService, mock_db: AsyncMock):
        existing_user = User(
            id=uuid.uuid4(), email="test@example.com", name="Existing"
        )
        mock_db.execute.return_value.scalar_one_or_none.return_value = existing_user

        with pytest.raises(ConflictError, match="Email already registered"):
            await auth_service.register("Test", "test@example.com", "securePass123")


class TestLogin:
    async def test_login_success(self, auth_service: AuthService, mock_db: AsyncMock):
        from app.core.security import hash_password
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            name="Test",
            passwordHash=hash_password("securePass123"),
        )
        mock_db.execute.return_value.scalar_one_or_none.return_value = user

        result_user, token = await auth_service.login("test@example.com", "securePass123")

        assert result_user.email == "test@example.com"
        assert token is not None

    async def test_login_wrong_password(self, auth_service: AuthService, mock_db: AsyncMock):
        from app.core.security import hash_password
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            passwordHash=hash_password("correctPass"),
        )
        mock_db.execute.return_value.scalar_one_or_none.return_value = user

        with pytest.raises(UnauthorizedError, match="Invalid email or password"):
            await auth_service.login("test@example.com", "wrongPass")

    async def test_login_nonexistent_email(self, auth_service: AuthService, mock_db: AsyncMock):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(UnauthorizedError, match="Invalid email or password"):
            await auth_service.login("nonexistent@example.com", "somePass")


class TestOtpFlow:
    async def test_forgot_password_nonexistent_returns_empty(self, auth_service: AuthService, mock_db: AsyncMock):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        otp = await auth_service.forgot_password("nobody@example.com")

        assert otp == ""
        assert not mock_db.add.called

    async def test_forgot_password_generates_otp(self, auth_service: AuthService, mock_db: AsyncMock):
        user = User(id=uuid.uuid4(), email="test@example.com")
        mock_db.execute.return_value.scalar_one_or_none.return_value = user

        otp = await auth_service.forgot_password("test@example.com")

        assert len(otp) == 6
        assert otp.isdigit()
        assert mock_db.add.called

    async def test_verify_otp_invalid(self, auth_service: AuthService, mock_db: AsyncMock):
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(BadRequestError, match="Invalid OTP"):
            await auth_service.verify_otp("test@example.com", "000000")

    async def test_verify_otp_expired(self, auth_service: AuthService, mock_db: AsyncMock):
        from app.models.user import VerificationToken
        from datetime import timedelta
        vt = MagicMock(spec=VerificationToken)
        vt.expires = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_db.execute.return_value.scalar_one_or_none.return_value = vt

        with pytest.raises(BadRequestError, match="OTP expired"):
            await auth_service.verify_otp("test@example.com", "123456")

    async def test_verify_otp_success(self, auth_service: AuthService, mock_db: AsyncMock):
        from app.models.user import VerificationToken
        from datetime import timedelta
        vt = MagicMock(spec=VerificationToken)
        vt.expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        vt.token = "123456"
        mock_db.execute.return_value.scalar_one_or_none.return_value = vt

        reset_token = await auth_service.verify_otp("test@example.com", "123456")

        assert reset_token is not None
        assert isinstance(reset_token, str)
        assert mock_db.delete.called

    async def test_reset_password_success(self, auth_service: AuthService, mock_db: AsyncMock):
        from app.core.security import encrypt_data
        reset_data = f"test@example.com:{datetime.now(timezone.utc).isoformat()}"
        reset_token = encrypt_data(reset_data)

        user = MagicMock(spec=User)
        user.id = uuid.uuid4()
        user.email = "test@example.com"
        user.passwordHash = "old_hash"
        mock_db.execute.return_value.scalar_one_or_none.return_value = user

        await auth_service.reset_password(reset_token, "newSecurePass123")

        assert user.passwordHash != "old_hash"
        assert mock_db.flush.called

    async def test_reset_password_expired_token(self, auth_service: AuthService, mock_db: AsyncMock):
        from app.core.security import encrypt_data
        from datetime import timedelta
        old_time = datetime.now(timezone.utc) - timedelta(hours=1)
        reset_data = f"test@example.com:{old_time.isoformat()}"
        reset_token = encrypt_data(reset_data)

        with pytest.raises(BadRequestError, match="Reset token expired"):
            await auth_service.reset_password(reset_token, "newPass123")


class TestGoogleOAuth:
    async def test_google_callback_missing_state(self, auth_service: AuthService, mock_db: AsyncMock):
        with pytest.raises(UnauthorizedError, match="Invalid OAuth state"):
            await auth_service.google_callback("some-code", "", "expected-state")

    async def test_google_callback_wrong_state(self, auth_service: AuthService, mock_db: AsyncMock):
        with pytest.raises(UnauthorizedError, match="Invalid OAuth state"):
            await auth_service.google_callback("some-code", "attacker-state", "expected-state")

    async def test_google_login_url_returns_state(self):
        from unittest.mock import patch
        service = AuthService(None)
        with patch("authlib.integrations.httpx_client.OAuth2Client") as mock_cls:
            client = MagicMock()
            client.create_authorization_url.return_value = (
                "https://accounts.google.com/authorize?xyz",
                "state-token-123",
            )
            mock_cls.return_value = client
            uri, state = await service.google_login_url()
            assert uri.startswith("https://accounts.google.com")
            assert state == "state-token-123"
