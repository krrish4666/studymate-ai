import uuid
from datetime import datetime

from sqlalchemy import Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    emailVerified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    image: Mapped[str | None] = mapped_column(Text, nullable=True)
    passwordHash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    accounts: Mapped[list["Account"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    file_records: Mapped[list["FileRecord"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    session_outputs: Mapped[list["SessionOutput"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Account(UUIDMixin, Base):
    __tablename__ = "accounts"

    userId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    providerAccountId: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    scope: Mapped[str | None] = mapped_column(String(255), nullable=True)
    id_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_state: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship(back_populates="accounts")


class Session(UUIDMixin, Base):
    __tablename__ = "sessions"

    sessionToken: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    userId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship(back_populates="sessions")


class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    identifier: Mapped[str] = mapped_column(String(255), primary_key=True)
    token: Mapped[str] = mapped_column(String(255), primary_key=True)
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
