"""Separate load-test traffic from real user traffic.

Revision ID: 20260913_0010
Revises: 20260913_0009
Create Date: 2026-09-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_0010"
down_revision: str | None = "20260913_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table_name in ("agent_runs", "rag_queries"):
        op.add_column(
            table_name,
            sa.Column("traffic_class", sa.String(length=20), server_default="user", nullable=False),
        )
        op.create_check_constraint(
            f"ck_{table_name}_traffic_class",
            table_name,
            "traffic_class IN ('user', 'load_test')",
        )
        op.create_index(
            f"ix_{table_name}_traffic_created",
            table_name,
            ["traffic_class", "created_at"],
        )
    op.add_column(
        "http_request_metrics",
        sa.Column("traffic_class", sa.String(length=20), server_default="user", nullable=False),
    )
    op.create_check_constraint(
        "ck_http_metrics_traffic_class",
        "http_request_metrics",
        "traffic_class IN ('user', 'load_test')",
    )
    op.create_index(
        "ix_http_metrics_traffic_created",
        "http_request_metrics",
        ["traffic_class", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_http_metrics_traffic_created", table_name="http_request_metrics")
    op.drop_constraint("ck_http_metrics_traffic_class", "http_request_metrics", type_="check")
    op.drop_column("http_request_metrics", "traffic_class")
    for table_name in ("rag_queries", "agent_runs"):
        op.drop_index(f"ix_{table_name}_traffic_created", table_name=table_name)
        op.drop_constraint(f"ck_{table_name}_traffic_class", table_name, type_="check")
        op.drop_column(table_name, "traffic_class")
