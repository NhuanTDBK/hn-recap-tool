"""add_user_activity_log_table

Revision ID: 20260225001
Revises: e7a718d85a59
Create Date: 2026-02-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '20260225001'
down_revision: Union[str, None] = 'e7a718d85a59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_activity_log table
    op.create_table(
        'user_activity_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action_type', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_user_activity_log_user_id', 'user_activity_log', ['user_id'], unique=False)
    op.create_index('ix_user_activity_log_post_id', 'user_activity_log', ['post_id'], unique=False)
    op.create_index('ix_user_activity_log_action_type', 'user_activity_log', ['action_type'], unique=False)
    op.create_index('ix_user_activity_log_created_at', 'user_activity_log', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_user_activity_log_created_at', table_name='user_activity_log')
    op.drop_index('ix_user_activity_log_action_type', table_name='user_activity_log')
    op.drop_index('ix_user_activity_log_post_id', table_name='user_activity_log')
    op.drop_index('ix_user_activity_log_user_id', table_name='user_activity_log')

    # Drop table
    op.drop_table('user_activity_log')
