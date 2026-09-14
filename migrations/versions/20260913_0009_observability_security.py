"""Add Phase 6 operational observability records.

Revision ID: 20260913_0009
Revises: 20260913_0008
Create Date: 2026-09-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_0009"
down_revision: str | None = "20260913_0008"
_branch_labels: str | Sequence[str] | None = None
branch_labels = _branch_labels
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("trace_id", sa.String(length=32), nullable=True))
    op.create_index("ix_agent_runs_trace_id", "agent_runs", ["trace_id"])
    op.add_column("rag_queries", sa.Column("trace_id", sa.String(length=32), nullable=True))
    op.create_index("ix_rag_queries_trace_id", "rag_queries", ["trace_id"])
    op.create_table(
        "http_request_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("trace_id", sa.String(length=32), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("status_code BETWEEN 100 AND 599", name="ck_http_metrics_status"),
        sa.CheckConstraint("duration_ms >= 0", name="ck_http_metrics_latency"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index("ix_http_metrics_created", "http_request_metrics", ["created_at"])
    op.create_index(
        "ix_http_metrics_status_created", "http_request_metrics", ["status_code", "created_at"]
    )
    op.create_index("ix_http_metrics_trace_id", "http_request_metrics", ["trace_id"])


def downgrade() -> None:
    op.drop_index("ix_http_metrics_trace_id", table_name="http_request_metrics")
    op.drop_index("ix_http_metrics_status_created", table_name="http_request_metrics")
    op.drop_index("ix_http_metrics_created", table_name="http_request_metrics")
    op.drop_table("http_request_metrics")
    op.drop_index("ix_rag_queries_trace_id", table_name="rag_queries")
    op.drop_column("rag_queries", "trace_id")
    op.drop_index("ix_agent_runs_trace_id", table_name="agent_runs")
    op.drop_column("agent_runs", "trace_id")
