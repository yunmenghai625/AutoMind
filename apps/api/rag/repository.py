from typing import Any, Protocol
from uuid import UUID

from apps.api.rag.entities import ChunkDraft, DocumentSummary, RetrievalHit


class KnowledgeRepository(Protocol):
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
    ) -> DocumentSummary: ...

    async def list_documents(self) -> list[DocumentSummary]: ...

    async def create_query(self, *, request_id: str, original_query: str) -> UUID: ...

    async def hybrid_search(
        self,
        *,
        query_embedding: list[float],
        fts_query: str,
        limit: int,
    ) -> list[RetrievalHit]: ...

    async def record_hits(
        self,
        *,
        query_id: UUID,
        attempt: int,
        hits: list[RetrievalHit],
        selected_ids: set[UUID],
    ) -> None: ...

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
    ) -> None: ...

    async def fail_query(self, *, query_id: UUID, error_code: str) -> None: ...
