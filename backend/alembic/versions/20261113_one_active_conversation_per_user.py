"""Allow only one active conversation per user

A race between two discussion messages could leave a user with two rows where
ended_at IS NULL. Lookups then had no single "active" conversation. This ends
all but the newest active conversation per user, then enforces the rule with a
partial unique index.

Revision ID: 20261113001
Revises: 20261111001
Create Date: 2026-11-13

"""
from collections.abc import Sequence

from alembic import op

revision: str = "20261113001"
down_revision: str | None = "20261111001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "uq_conversations_one_active_per_user"


def upgrade() -> None:
    # Keep the newest active conversation per user; close the rest.
    op.execute(
        """
        UPDATE conversations
        SET ended_at = now()
        WHERE ended_at IS NULL
          AND id NOT IN (
              SELECT DISTINCT ON (user_id) id
              FROM conversations
              WHERE ended_at IS NULL
              ORDER BY user_id, started_at DESC
          )
        """
    )
    op.create_index(
        INDEX_NAME,
        "conversations",
        ["user_id"],
        unique=True,
        postgresql_where="ended_at IS NULL",
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="conversations")
