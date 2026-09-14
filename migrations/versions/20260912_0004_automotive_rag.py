"""Create Phase 3 automotive RAG tables and pgvector indexes.

Revision ID: 20260912_0004
Revises: 20260912_0003
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260912_0004"
down_revision: str | None = "20260912_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_key", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("page_count >= 0 AND chunk_count >= 0", name="ck_documents_counts"),
        sa.CheckConstraint("version > 0", name="ck_documents_version_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key"),
    )
    op.create_index("ix_documents_status_updated", "documents", ["status", "updated_at"])

    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(length=300), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("fts_text", sa.Text(), nullable=False),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('simple', coalesce(fts_text, ''))", persisted=True),
            nullable=False,
        ),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(dim=384), nullable=False),
        sa.Column("embedding_model", sa.String(length=160), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("ordinal >= 0", name="ck_chunks_ordinal_nonnegative"),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number > 0", name="ck_chunks_page_positive"
        ),
        sa.CheckConstraint("token_count > 0", name="ck_chunks_token_count_positive"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ux_chunks_document_ordinal", "chunks", ["document_id", "ordinal"], unique=True)
    op.create_index("ix_chunks_search_vector", "chunks", ["search_vector"], postgresql_using="gin")
    op.create_index(
        "ix_chunks_embedding_hnsw",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "rag_queries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("original_query", sa.Text(), nullable=False),
        sa.Column("rewritten_query", sa.Text(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("retrieved_count", sa.Integer(), nullable=False),
        sa.Column("low_confidence", sa.Boolean(), nullable=False),
        sa.Column("top_score", sa.Float(), nullable=True),
        sa.Column("vector_search_ms", sa.Integer(), nullable=False),
        sa.Column("rerank_ms", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("retry_count BETWEEN 0 AND 2", name="ck_rag_queries_retry_count"),
        sa.CheckConstraint("retrieved_count >= 0", name="ck_rag_queries_retrieved_count"),
        sa.CheckConstraint(
            "vector_search_ms >= 0 AND rerank_ms >= 0", name="ck_rag_queries_latency"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index("ix_rag_queries_created_at", "rag_queries", ["created_at"])
    op.create_index("ix_rag_queries_status_created", "rag_queries", ["status", "created_at"])

    op.create_table(
        "rag_hits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("query_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("vector_score", sa.Float(), nullable=False),
        sa.Column("text_score", sa.Float(), nullable=False),
        sa.Column("hybrid_score", sa.Float(), nullable=False),
        sa.Column("rerank_score", sa.Float(), nullable=True),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("attempt BETWEEN 0 AND 2", name="ck_rag_hits_attempt"),
        sa.CheckConstraint("rank > 0", name="ck_rag_hits_rank_positive"),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["query_id"], ["rag_queries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rag_hits_query_attempt_rank", "rag_hits", ["query_id", "attempt", "rank"])


def downgrade() -> None:
    op.drop_index("ix_rag_hits_query_attempt_rank", table_name="rag_hits")
    op.drop_table("rag_hits")
    op.drop_index("ix_rag_queries_status_created", table_name="rag_queries")
    op.drop_index("ix_rag_queries_created_at", table_name="rag_queries")
    op.drop_table("rag_queries")
    op.drop_index("ix_chunks_embedding_hnsw", table_name="chunks")
    op.drop_index("ix_chunks_search_vector", table_name="chunks")
    op.drop_index("ux_chunks_document_ordinal", table_name="chunks")
    op.drop_table("chunks")
    op.drop_index("ix_documents_status_updated", table_name="documents")
    op.drop_table("documents")
