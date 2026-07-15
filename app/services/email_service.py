from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

from app.config import settings


class EmailService:
    def __init__(self):
        self._config = None

    @property
    def config(self) -> ConnectionConfig:
        if self._config is None:
            self._config = ConnectionConfig(
                MAIL_USERNAME=settings.SMTP_USERNAME,
                MAIL_PASSWORD=settings.SMTP_PASSWORD,
                MAIL_FROM=settings.SMTP_USERNAME,
                MAIL_PORT=settings.SMTP_PORT,
                MAIL_SERVER=settings.SMTP_SERVER,
                MAIL_STARTTLS=True,
                MAIL_SSL_TLS=False,
                USE_CREDENTIALS=True,
            )
        return self._config

    async def send_otp(self, email: str, otp: str) -> None:
        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            return

        message = MessageSchema(
            subject="StudyMate AI HUB - Password Reset OTP",
            recipients=[email],
            body=f"""
            <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
                <h2 style="color: #d97706;">StudyMate AI HUB</h2>
                <p>Your password reset OTP is:</p>
                <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px;
                            text-align: center; padding: 20px; background: #fef3c7;
                            border-radius: 8px; margin: 16px 0;">{otp}</div>
                <p>This OTP expires in <strong>15 minutes</strong>.</p>
                <p style="color: #6b7280; font-size: 12px;">If you didn't request this, ignore this email.</p>
            </div>
            """,
            subtype="html",
        )
        fm = FastMail(self.config)
        await fm.send_message(message)


email_service = EmailService()
