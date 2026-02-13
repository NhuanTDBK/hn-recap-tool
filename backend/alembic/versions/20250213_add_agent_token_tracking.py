"""add agent token tracking tables

Revision ID: 20250213_add_agent
Revises: 7be4bb0d3cdd
Create Date: 2025-02-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20250213_add_agent"
down_revision: Union[str, None] = "7be4bb0d3cdd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table (if not exists - needed for foreign keys)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("interests", sa.JSON(), nullable=True),
        sa.Column("memory_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("status", sa.String(50), server_default="active", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index(op.f("ix_users_telegram_id"), "users", ["telegram_id"], unique=True)

    # Per-user daily token usage
    op.create_table(
        "user_token_usage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("model", sa.String(50), nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 6), server_default="0", nullable=False),
        sa.Column("request_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "date", "model", name="uq_user_token_usage"),
    )
    op.create_index(op.f("ix_user_token_usage_user_id_date"), "user_token_usage", ["user_id", "date"], unique=False)
    op.create_index(op.f("ix_user_token_usage_date"), "user_token_usage", ["date"], unique=False)

    # Individual agent calls for detailed tracking
    op.create_table(
        "agent_calls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("trace_id", sa.String(255), nullable=True),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("operation", sa.String(100), nullable=True),
        sa.Column("model", sa.String(50), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), server_default="success", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_agent_calls_user_id"), "agent_calls", ["user_id"], unique=False)
    op.create_index(op.f("ix_agent_calls_created_at"), "agent_calls", ["created_at"], unique=False)
    op.create_index(op.f("ix_agent_calls_trace_id"), "agent_calls", ["trace_id"], unique=False)
    op.create_index(op.f("ix_agent_calls_agent_name"), "agent_calls", ["agent_name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_calls_agent_name"), table_name="agent_calls")
    op.drop_index(op.f("ix_agent_calls_trace_id"), table_name="agent_calls")
    op.drop_index(op.f("ix_agent_calls_created_at"), table_name="agent_calls")
    op.drop_index(op.f("ix_agent_calls_user_id"), table_name="agent_calls")
    op.drop_table("agent_calls")

    op.drop_index(op.f("ix_user_token_usage_date"), table_name="user_token_usage")
    op.drop_index(op.f("ix_user_token_usage_user_id_date"), table_name="user_token_usage")
    op.drop_table("user_token_usage")

    op.drop_index(op.f("ix_users_telegram_id"), table_name="users")
    op.drop_table("users")
