"""widen users.telegram_id to bigint

Telegram supergroup chat IDs (-100xxxxxxxxxx) and newer user IDs do not fit in
int32. The group feed is stored as a users row keyed by its chat ID.

Revision ID: 20261016001
Revises: 20260225001
Create Date: 2026-10-16 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261016001"
down_revision: str | None = "20260225001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "telegram_id",
        type_=sa.BigInteger(),
        existing_type=sa.Integer(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "telegram_id",
        type_=sa.Integer(),
        existing_type=sa.BigInteger(),
        existing_nullable=False,
    )
