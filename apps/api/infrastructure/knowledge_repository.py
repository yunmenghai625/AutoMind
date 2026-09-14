from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.request_context import trace_id_context, traffic_class_context
from apps.api.core.telemetry import record_operation
from apps.api.infrastructure.models import (
    KnowledgeChunkRecord,
    KnowledgeDocumentRecord,
    RagHitRecord,
    RagQueryRecord,
)
from apps.api.rag.entities import ChunkDraft, DocumentSummary, RetrievalHit
from apps.api.rag.text import lexical_tokens


class PostgresKnowledgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_document(
        self,
        *,
        source_key: str,
        title: str,
        description: str,
        source_type: str,
        source_uri: str | None,
        checksum_sha256: str,
        metadata: dict[str, Any],
        chunks: list[ChunkDraft],
    ) -> DocumentSummary:
        async with self._session.begin():
            page_count = len(
                {chunk.page_number for chunk in chunks if chunk.page_number is not None}
            )
            document = (
                await self._session.scalars(
                    select(KnowledgeDocumentRecord)
                    .where(KnowledgeDocumentRecord.source_key == source_key)
                    .with_for_update()
                )
            ).one_or_none()
            if (
                document is not None
                and document.checksum_sha256 == checksum_sha256
                and document.status == "indexed"
            ):
                document.title = title
                document.description = description
                document.source_type = source_type
                document.source_uri = source_uri
                document.metadata_json = metadata
                document.page_count = page_count
                document.chunk_count = len(chunks)
                await self._session.flush()
                await self._session.refresh(document)
                return _document_summary(document)

            if document is None:
                document = KnowledgeDocumentRecord(id=uuid4(), source_key=source_key, version=1)
                self._session.add(document)
            else:
                await self._session.execute(
                    delete(KnowledgeChunkRecord).where(
                        KnowledgeChunkRecord.document_id == document.id
                    )
                )
                document.version += 1

            document.title = title
            document.description = description
            document.source_type = source_type
            document.source_uri = source_uri
            document.checksum_sha256 = checksum_sha256
            document.status = "indexed"
            document.metadata_json = metadata
            document.page_count = page_count
            document.chunk_count = len(chunks)
            # Chunks reference the UUID directly rather than through an ORM
            # relationship, so persist the parent before batching child rows.
            await self._session.flush()

            for chunk in chunks:
                if chunk.embedding is None or chunk.embedding_model is None:
                    raise ValueError("Every chunk must have an embedding")
                self._session.add(
                    KnowledgeChunkRecord(
                        id=uuid4(),
                        document_id=document.id,
                        ordinal=chunk.ordinal,
                        section=chunk.section,
                        page_number=chunk.page_number,
                        content=chunk.content,
                        fts_text=chunk.fts_text,
                        embedding=chunk.embedding,
                        embedding_model=chunk.embedding_model,
                        metadata_json=chunk.metadata,
                        token_count=chunk.token_count,
                    )
                )
            await self._session.flush()
            await self._session.refresh(document)
            return _document_summary(document)

    async def list_documents(self) -> list[DocumentSummary]:
        async with self._session.begin():
            documents = (
                await self._session.scalars(
                    select(KnowledgeDocumentRecord).order_by(
                        KnowledgeDocumentRecord.updated_at.desc()
                    )
                )
            ).all()
            return [_document_summary(document) for document in documents]

    async def create_query(self, *, request_id: str, original_query: str) -> UUID:
        query_id = uuid4()
        async with self._session.begin():
            self._session.add(
                RagQueryRecord(
                    id=query_id,
                    request_id=request_id,
                    trace_id=trace_id_context.get(),
                    traffic_class=traffic_class_context.get(),
                    original_query=original_query,
                    rewritten_query=original_query,
                    status="running",
                )
            )
        return query_id

    async def hybrid_search(
        self,
        *,
        query_embedding: list[float],
        fts_query: str,
        limit: int,
    ) -> list[RetrievalHit]:
        tokens = list(dict.fromkeys(lexical_tokens(fts_query)))[:64]
        ts_query_text = " | ".join(tokens) or "automind_no_match"
        ts_query = func.to_tsquery("simple", ts_query_text)
        cosine_distance = KnowledgeChunkRecord.embedding.cosine_distance(query_embedding)
        vector_score = func.greatest(0.0, 1.0 - cosine_distance)
        text_score = func.ts_rank_cd(KnowledgeChunkRecord.search_vector, ts_query, 32)
        normalized_text_score = func.least(1.0, text_score * 5.0)
        hybrid_score = vector_score * 0.7 + normalized_text_score * 0.3
        candidate_limit = max(50, limit * 3)
        vector_candidates = (
            select(KnowledgeChunkRecord.id)
            .join(
                KnowledgeDocumentRecord,
                KnowledgeDocumentRecord.id == KnowledgeChunkRecord.document_id,
            )
            .where(KnowledgeDocumentRecord.status == "indexed")
            .order_by(cosine_distance)
            .limit(candidate_limit)
        )
        text_candidates = (
            select(KnowledgeChunkRecord.id)
            .join(
                KnowledgeDocumentRecord,
                KnowledgeDocumentRecord.id == KnowledgeChunkRecord.document_id,
            )
            .where(
                KnowledgeDocumentRecord.status == "indexed",
                KnowledgeChunkRecord.search_vector.op("@@")(ts_query),
            )
            .order_by(text_score.desc())
            .limit(candidate_limit)
        )
        async with self._session.begin():
            vector_ids = set(await self._session.scalars(vector_candidates))
            text_ids = set(await self._session.scalars(text_candidates))
            candidate_ids = vector_ids | text_ids
            if not candidate_ids:
                return []
            statement = (
                select(
                    KnowledgeChunkRecord,
                    KnowledgeDocumentRecord,
                    vector_score.label("vector_score"),
                    text_score.label("text_score"),
                    hybrid_score.label("hybrid_score"),
                )
                .join(
                    KnowledgeDocumentRecord,
                    KnowledgeDocumentRecord.id == KnowledgeChunkRecord.document_id,
                )
                .where(KnowledgeChunkRecord.id.in_(candidate_ids))
                .order_by(hybrid_score.desc())
                .limit(limit)
            )
            rows = (await self._session.execute(statement)).all()
            return [
                RetrievalHit(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    source_key=document.source_key,
                    title=document.title,
                    section=chunk.section,
                    page_number=chunk.page_number,
                    content=chunk.content,
                    vector_score=float(raw_vector_score or 0),
                    text_score=float(raw_text_score or 0),
                    hybrid_score=float(raw_hybrid_score or 0),
                )
                for chunk, document, raw_vector_score, raw_text_score, raw_hybrid_score in rows
            ]

    async def record_hits(
        self,
        *,
        query_id: UUID,
        attempt: int,
        hits: list[RetrievalHit],
        selected_ids: set[UUID],
    ) -> None:
        async with self._session.begin():
            for rank, hit in enumerate(hits, start=1):
                self._session.add(
                    RagHitRecord(
                        id=uuid4(),
                        query_id=query_id,
                        chunk_id=hit.chunk_id,
                        attempt=attempt,
                        rank=rank,
                        vector_score=hit.vector_score,
                        text_score=hit.text_score,
                        hybrid_score=hit.hybrid_score,
                        rerank_score=hit.rerank_score,
                        selected=hit.chunk_id in selected_ids,
                    )
                )

    async def complete_query(
        self,
        *,
        query_id: UUID,
        rewritten_query: str,
        answer_text: str,
        status: str,
        retry_count: int,
        retrieved_count: int,
        low_confidence: bool,
        top_score: float | None,
        vector_search_ms: int,
        rerank_ms: int,
    ) -> None:
        record_operation(
            "rag",
            status=status,
            latency_ms=vector_search_ms + rerank_ms,
            name="hybrid_search",
        )
        async with self._session.begin():
            await self._session.execute(
                update(RagQueryRecord)
                .where(RagQueryRecord.id == query_id)
                .values(
                    rewritten_query=rewritten_query,
                    answer_text=answer_text,
                    status=status,
                    retry_count=retry_count,
                    retrieved_count=retrieved_count,
                    low_confidence=low_confidence,
                    top_score=top_score,
                    vector_search_ms=vector_search_ms,
                    rerank_ms=rerank_ms,
                    completed_at=datetime.now(UTC),
                )
            )

    async def fail_query(self, *, query_id: UUID, error_code: str) -> None:
        record_operation("rag", status="failed", latency_ms=0, name="hybrid_search")
        async with self._session.begin():
            await self._session.execute(
                update(RagQueryRecord)
                .where(RagQueryRecord.id == query_id)
                .values(
                    status="failed",
                    error_code=error_code,
                    completed_at=datetime.now(UTC),
                )
            )


def _document_summary(document: KnowledgeDocumentRecord) -> DocumentSummary:
    return DocumentSummary(
        id=document.id,
        source_key=document.source_key,
        title=document.title,
        description=document.description or "",
        status=document.status,
        chunk_count=document.chunk_count,
        updated_at=document.updated_at,
    )
