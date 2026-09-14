"""Create Phase 2 Agent runtime audit tables.

Revision ID: 20260912_0003
Revises: 20260912_0002
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260912_0003"
down_revision: str | None = "20260912_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("agent_name", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("token_in", sa.Integer(), nullable=False),
        sa.Column("token_out", sa.Integer(), nullable=False),
        sa.Column("cost_est_cny", sa.Numeric(12, 6), nullable=False),
        sa.Column("llm_calls", sa.Integer(), nullable=False),
        sa.Column("response_summary", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("latency_ms >= 0", name="ck_agent_runs_latency_nonnegative"),
        sa.CheckConstraint(
            "token_in >= 0 AND token_out >= 0", name="ck_agent_runs_tokens_nonnegative"
        ),
        sa.CheckConstraint("llm_calls >= 0", name="ck_agent_runs_llm_calls_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index("ix_agent_runs_conversation_id", "agent_runs", ["conversation_id"])
    op.create_index("ix_agent_runs_created_at", "agent_runs", ["created_at"])

    op.create_table(
        "agent_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("node_name", sa.String(length=80), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("sequence > 0", name="ck_agent_steps_sequence_positive"),
        sa.CheckConstraint("latency_ms >= 0", name="ck_agent_steps_latency_nonnegative"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ux_agent_steps_run_sequence", "agent_steps", ["run_id", "sequence"], unique=True
    )

    op.create_table(
        "tool_calls",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("arguments_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("safety_decision", sa.String(length=20), nullable=False),
        sa.Column("safety_code", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("latency_ms >= 0", name="ck_tool_calls_latency_nonnegative"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tool_calls_run_created", "tool_calls", ["run_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_tool_calls_run_created", table_name="tool_calls")
    op.drop_table("tool_calls")
    op.drop_index("ux_agent_steps_run_sequence", table_name="agent_steps")
    op.drop_table("agent_steps")
    op.drop_index("ix_agent_runs_created_at", table_name="agent_runs")
    op.drop_index("ix_agent_runs_conversation_id", table_name="agent_runs")
    op.drop_table("agent_runs")
