from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    ordinal: int
    section: str | None
    page_number: int | None
    content: str
    fts_text: str
    token_count: int
    metadata: dict[str, Any]
    embedding: list[float] | None = None
    embedding_model: str | None = None

    def with_embedding(self, vector: list[float], model: str) -> "ChunkDraft":
        return replace(self, embedding=vector, embedding_model=model)


@dataclass(frozen=True, slots=True)
class DocumentSummary:
    id: UUID
    source_key: str
    title: str
    description: str
    status: str
    chunk_count: int
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    chunk_id: UUID
    document_id: UUID
    source_key: str
    title: str
    section: str | None
    page_number: int | None
    content: str
    vector_score: float
    text_score: float
    hybrid_score: float
    rerank_score: float | None = None

    def with_rerank_score(self, score: float) -> "RetrievalHit":
        return replace(self, rerank_score=score)


@dataclass(frozen=True, slots=True)
class CitationData:
    source: str
    chapter: str | None
    page: int | None
    snippet: str


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    original_query: str
    rewritten_query: str
    retrieved_documents: int
    reranker_enabled: bool
    vector_search_ms: int
    rerank_ms: int
    retry_count: int
    query_id: UUID


@dataclass(frozen=True, slots=True)
class KnowledgeResult:
    answer: str
    citations: list[CitationData]
    retrieval: RetrievalMetrics
