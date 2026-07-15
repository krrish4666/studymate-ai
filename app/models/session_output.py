import uuid

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class SessionOutput(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "session_outputs"

    fileRecordId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_records.id", ondelete="SET NULL"), nullable=True
    )
    userId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feature: Mapped[str] = mapped_column(String(50), nullable=False)
    outputJson: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    outputText: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdfUrl: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="session_outputs")
    file_record: Mapped["FileRecord | None"] = relationship(back_populates="session_outputs")
