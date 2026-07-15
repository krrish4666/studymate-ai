from unittest.mock import AsyncMock, patch

import pytest

from app.services.email_service import email_service
from app.config import settings


class TestEmailService:
    async def test_send_otp_skipped_when_no_credentials(self):
        with patch.object(settings, "SMTP_USERNAME", ""), \
             patch.object(settings, "SMTP_PASSWORD", ""):
            result = await email_service.send_otp("test@example.com", "123456")
            assert result is None

    async def test_send_otp_calls_fastmail(self):
        with patch.object(settings, "SMTP_USERNAME", "test@gmail.com"), \
             patch.object(settings, "SMTP_PASSWORD", "app-password"), \
             patch("app.services.email_service.FastMail.send_message", new_callable=AsyncMock) as mock_send:
            await email_service.send_otp("test@example.com", "123456")
            assert mock_send.called
