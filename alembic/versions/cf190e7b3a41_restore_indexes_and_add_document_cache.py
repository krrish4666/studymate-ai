"""restore dropped indexes and add document_cache table

Revision ID: cf190e7b3a41
Revises: b896cee64be4
Create Date: 2026-09-15 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "cf190e7b3a41"
down_revision: Union[str, Sequence[str], None] = "b896cee64be4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Re-create objects that the b896cee64be4 migration incorrectly dropped.
    op.create_index(op.f("ix_accounts_userId"), "accounts", ["userId"], unique=False)
    op.create_unique_constraint(
        op.f("uq_accounts_provider"),
        "accounts",
        ["provider", "providerAccountId"],
    )
    op.create_index(
        op.f("ix_session_outputs_fileRecordId"),
        "session_outputs",
        ["fileRecordId"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sessions_userId"), "sessions", ["userId"], unique=False
    )

    # document_cache was modelled but never created by migrations.
    op.create_table(
        "document_cache",
        sa.Column(
            "fileRecordId",
            UUID(as_uuid=True),
            sa.ForeignKey("file_records.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("extractedText", sa.Text, nullable=False),
        sa.Column(
            "createdAt",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Enforce at most one active Gemini key per user at the DB level.
    op.create_index(
        "uq_api_keys_active_user",
        "api_keys",
        ["userId"],
        unique=True,
        postgresql_where=sa.text("isActive = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_api_keys_active_user", table_name="api_keys")
    op.drop_table("document_cache")
    op.drop_index(op.f("ix_sessions_userId"), table_name="sessions")
    op.drop_index(
        op.f("ix_session_outputs_fileRecordId"), table_name="session_outputs"
    )
    op.drop_constraint(op.f("uq_accounts_provider"), "accounts", type_="unique")
    op.drop_index(op.f("ix_accounts_userId"), table_name="accounts")