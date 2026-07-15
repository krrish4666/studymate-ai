"""initial_schema

Revision ID: cb1a701843c2
Revises:
Create Date: 2026-07-15 22:25:29.400988

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "cb1a701843c2"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("emailVerified", sa.DateTime(timezone=True), nullable=True),
        sa.Column("image", sa.Text, nullable=True),
        sa.Column("passwordHash", sa.String(255), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("userId", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("providerAccountId", sa.String(255), nullable=False),
        sa.Column("refresh_token", sa.Text, nullable=True),
        sa.Column("access_token", sa.Text, nullable=True),
        sa.Column("expires_at", sa.Integer, nullable=True),
        sa.Column("token_type", sa.String(50), nullable=True),
        sa.Column("scope", sa.String(255), nullable=True),
        sa.Column("id_token", sa.Text, nullable=True),
        sa.Column("session_state", sa.String(255), nullable=True),
        sa.UniqueConstraint("provider", "providerAccountId", name="uq_accounts_provider"),
    )
    op.create_index("ix_accounts_userId", "accounts", ["userId"])

    op.create_table(
        "sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("sessionToken", sa.String(255), nullable=False, unique=True),
        sa.Column("userId", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sessions_userId", "sessions", ["userId"])

    op.create_table(
        "verification_tokens",
        sa.Column("identifier", sa.String(255), primary_key=True),
        sa.Column("token", sa.String(255), primary_key=True),
        sa.Column("expires", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("userId", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("encryptedKey", sa.Text, nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("isActive", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "file_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("userId", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("originalName", sa.String(255), nullable=False),
        sa.Column("fileUrl", sa.Text, nullable=False),
        sa.Column("fileType", sa.String(50), nullable=False),
        sa.Column("fileSize", sa.Integer, nullable=True),
        sa.Column("feature", sa.String(50), nullable=False, index=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("errorMessage", sa.Text, nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "session_outputs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("fileRecordId", UUID(as_uuid=True), sa.ForeignKey("file_records.id", ondelete="SET NULL"), nullable=True),
        sa.Column("userId", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("feature", sa.String(50), nullable=False),
        sa.Column("outputJson", JSONB, nullable=True),
        sa.Column("outputText", sa.Text, nullable=True),
        sa.Column("pdfUrl", sa.Text, nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_session_outputs_fileRecordId", "session_outputs", ["fileRecordId"])


def downgrade() -> None:
    op.drop_table("session_outputs")
    op.drop_table("file_records")
    op.drop_table("api_keys")
    op.drop_table("verification_tokens")
    op.drop_table("sessions")
    op.drop_table("accounts")
    op.drop_table("users")
