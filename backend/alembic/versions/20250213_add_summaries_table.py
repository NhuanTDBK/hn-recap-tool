"""add summaries table for personalized summaries

Revision ID: 20250213_summaries
Revises: 20250213_add_agent
Create Date: 2025-02-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20250213_summaries"
down_revision: Union[str, None] = "20250213_add_agent"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create summaries table for personalized summaries
    op.create_table(
        "summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),  # NULL = default summary
        sa.Column("prompt_type", sa.String(50), nullable=False),  # basic, technical, business, etc.
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("key_points", sa.JSON(), nullable=True),  # Extracted key points if available
        sa.Column("technical_level", sa.String(50), nullable=True),  # beginner, intermediate, advanced
        sa.Column("token_count", sa.Integer(), nullable=True),  # Tokens used for this summary
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),  # Cost of generation
        sa.Column("rating", sa.Integer(), nullable=True),  # User rating 1-5
        sa.Column("user_feedback", sa.Text(), nullable=True),  # User feedback text
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_summaries_post_id"), "summaries", ["post_id"], unique=False)
    op.create_index(op.f("ix_summaries_user_id"), "summaries", ["user_id"], unique=False)
    op.create_index(op.f("ix_summaries_prompt_type"), "summaries", ["prompt_type"], unique=False)
    op.create_index(op.f("ix_summaries_created_at"), "summaries", ["created_at"], unique=False)
    op.create_index(
        op.f("ix_summaries_post_user"),
        "summaries",
        ["post_id", "user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_summaries_post_user"), table_name="summaries")
    op.drop_index(op.f("ix_summaries_created_at"), table_name="summaries")
    op.drop_index(op.f("ix_summaries_prompt_type"), table_name="summaries")
    op.drop_index(op.f("ix_summaries_user_id"), table_name="summaries")
    op.drop_index(op.f("ix_summaries_post_id"), table_name="summaries")
    op.drop_table("summaries")
