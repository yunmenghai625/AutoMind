from typing import Any

from pydantic import BaseModel, Field


class KnowledgeSource(BaseModel):
    id: str
    title: str
    description: str
    documents: int
    status: str
    updatedAt: str


class Citation(BaseModel):
    source: str
    chapter: str | None = None
    page: int | None = None
    snippet: str


class RetrievalDetails(BaseModel):
    originalQuery: str
    rewrittenQuery: str
    retrievedDocuments: int
    rerankerEnabled: bool
    vectorSearchMs: int
    rerankMs: int
    retryCount: int
    queryId: str


class KnowledgeAnswer(BaseModel):
    answer: str
    citations: list[Citation]
    retrieval: RetrievalDetails


class KnowledgeQueryRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)


class IngestDocumentRequest(BaseModel):
    sourceKey: str = Field(pattern=r"^[A-Za-z0-9_-]{1,160}$")
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=1000)
    content: str = Field(min_length=1, max_length=2_000_000)
    sourceUri: str | None = Field(default=None, max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestDocumentResponse(BaseModel):
    id: str
    sourceKey: str
    title: str
    status: str
    chunks: int
