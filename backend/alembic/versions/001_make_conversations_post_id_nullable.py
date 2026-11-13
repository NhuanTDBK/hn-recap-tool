"""Make conversations.post_id nullable for topic-based discussions

Revision ID: 001
Revises: 20261110001
Create Date: 2026-05-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "001_make_conversations_post_id_nullable"
down_revision: Union[str, None] = "20261110001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "conversations",
        "post_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
        existing_server_default=None,
    )


def downgrade() -> None:
    op.alter_column(
        "conversations",
        "post_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
        existing_server_default=None,
    )
