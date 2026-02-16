"""make_summaries_user_id_required_and_add_constraints

Revision ID: ca002ecaabd2
Revises: 38a5a14052f8
Create Date: 2026-02-15 15:37:56.809735

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca002ecaabd2'
down_revision: Union[str, None] = '38a5a14052f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make user_id NOT NULL and add constraints for personalized summarization.

    Changes:
    1. Delete existing summaries with user_id=NULL (shared summaries)
    2. Make user_id NOT NULL
    3. Add unique constraint on (post_id, user_id, prompt_type)
    4. Add composite index on (user_id, created_at) for time-based queries
    """
    # Step 1: Delete existing summaries with user_id=NULL
    # These are shared summaries from the old approach
    op.execute("DELETE FROM summaries WHERE user_id IS NULL")

    # Step 2: Make user_id NOT NULL
    op.alter_column('summaries', 'user_id',
                    existing_type=sa.Integer(),
                    nullable=False)

    # Step 3: Add unique constraint on (post_id, user_id, prompt_type)
    # This prevents duplicate summaries for same post/user/type combination
    op.create_unique_constraint(
        'uq_summaries_post_user_type',
        'summaries',
        ['post_id', 'user_id', 'prompt_type']
    )

    # Step 4: Add composite index for time-based queries
    # Used to find user's latest summary time
    op.create_index(
        'ix_summaries_user_created',
        'summaries',
        ['user_id', 'created_at']
    )


def downgrade() -> None:
    """Revert changes to allow shared summaries again."""
    # Drop new indexes and constraints
    op.drop_index('ix_summaries_user_created', table_name='summaries')
    op.drop_constraint('uq_summaries_post_user_type', 'summaries', type_='unique')

    # Make user_id nullable again
    op.alter_column('summaries', 'user_id',
                    existing_type=sa.Integer(),
                    nullable=True)
