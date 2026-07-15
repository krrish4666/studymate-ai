import uuid

from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class FileRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "file_records"

    userId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    originalName: Mapped[str] = mapped_column(String(255), nullable=False)
    fileUrl: Mapped[str] = mapped_column(Text, nullable=False)
    fileType: Mapped[str] = mapped_column(String(50), nullable=False)
    fileSize: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feature: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    errorMessage: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="file_records")
    session_outputs: Mapped[list["SessionOutput"]] = relationship(back_populates="file_record", cascade="all, delete-orphan")
