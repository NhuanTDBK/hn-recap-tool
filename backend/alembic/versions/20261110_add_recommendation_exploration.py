"""add topic, kind and quality to recommendations (explore/exploit)

Revision ID: 20261110001
Revises: 20261109001
Create Date: 2026-11-10 09:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20261110001"
down_revision: Union[str, None] = "20261109001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing picks all came from the profile, so they backfill as "exploit" with no topic.
    op.add_column(
        "recommendations", sa.Column("topic", sa.String(length=60), nullable=True)
    )
    op.add_column(
        "recommendations",
        sa.Column(
            "kind", sa.String(length=10), nullable=False, server_default="exploit"
        ),
    )
    op.add_column("recommendations", sa.Column("quality", sa.Integer(), nullable=True))
    op.create_index(
        "ix_recommendations_user_topic", "recommendations", ["user_id", "topic"]
    )


def downgrade() -> None:
    op.drop_index("ix_recommendations_user_topic", table_name="recommendations")
    op.drop_column("recommendations", "quality")
    op.drop_column("recommendations", "kind")
    op.drop_column("recommendations", "topic")
