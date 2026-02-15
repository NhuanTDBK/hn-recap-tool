"""add_summary_preferences_to_users

Revision ID: e7a718d85a59
Revises: aa19fc4f688a
Create Date: 2026-02-15 22:43:44.173489

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7a718d85a59'
down_revision: Union[str, None] = 'aa19fc4f688a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add summary_preferences JSON column with default value
    op.add_column(
        'users',
        sa.Column(
            'summary_preferences',
            sa.JSON(),
            nullable=True,
            server_default=sa.text("'{\"style\": \"basic\", \"detail_level\": \"medium\", \"technical_depth\": \"intermediate\"}'::json")
        )
    )

    # Backfill existing users with default preferences
    op.execute(
        "UPDATE users SET summary_preferences = '{\"style\": \"basic\", \"detail_level\": \"medium\", \"technical_depth\": \"intermediate\"}'::json "
        "WHERE summary_preferences IS NULL"
    )

    # Make column NOT NULL after backfill
    op.alter_column('users', 'summary_preferences', nullable=False)


def downgrade() -> None:
    # Drop the summary_preferences column
    op.drop_column('users', 'summary_preferences')
