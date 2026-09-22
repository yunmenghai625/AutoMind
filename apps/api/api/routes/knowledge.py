from typing import Annotated

from fastapi import APIRouter, Depends, Request

from apps.api.api.dependencies import (
    enforce_ai_admission,
    get_admin_identity,
    get_document_ingestion_service,
    get_knowledge_repository,
    get_knowledge_service,
)
from apps.api.auth.service import AuthIdentity
from apps.api.core.errors import AppError
from apps.api.infrastructure.knowledge_repository import PostgresKnowledgeRepository
from apps.api.rag.ingestion import DocumentIngestionError, DocumentIngestionService
from apps.api.rag.service import KnowledgeService
from apps.api.schemas.knowledge import (
    Citation,
    IngestDocumentRequest,
    IngestDocumentResponse,
    KnowledgeAnswer,
    KnowledgeQueryRequest,
    KnowledgeSource,
    RetrievalDetails,
)

router = APIRouter()


@router.get("/sources", response_model=list[KnowledgeSource])
async def list_knowledge_sources(
    repository: Annotated[PostgresKnowledgeRepository, Depends(get_knowledge_repository)],
) -> list[KnowledgeSource]:
    try:
        documents = await repository.list_documents()
    except Exception as exc:
        raise AppError(
            "KNOWLEDGE_STORAGE_UNAVAILABLE",
            "知识库暂时不可用",
            status_code=503,
        ) from exc
    return [
        KnowledgeSource(
            id=document.source_key,
            title=document.title,
            description=document.description,
            documents=1,
            status=document.status,
            updatedAt=document.updated_at.date().isoformat(),
        )
        for document in documents
    ]


@router.post("/documents/ingest", response_model=IngestDocumentResponse)
async def ingest_document(
    payload: IngestDocumentRequest,
    _admission: Annotated[None, Depends(enforce_ai_admission)],
    service: Annotated[DocumentIngestionService, Depends(get_document_ingestion_service)],
    _admin: Annotated[AuthIdentity, Depends(get_admin_identity)],
) -> IngestDocumentResponse:
    try:
        document = await service.ingest_markdown(
            source_key=payload.sourceKey,
            title=payload.title,
            description=payload.description,
            text=payload.content,
            source_uri=payload.sourceUri,
            metadata=payload.metadata,
        )
    except DocumentIngestionError as exc:
        raise AppError("DOCUMENT_INGESTION_INVALID", str(exc), status_code=422) from exc
    except Exception as exc:
        raise AppError("DOCUMENT_INGESTION_FAILED", "文档入库失败", status_code=503) from exc
    return IngestDocumentResponse(
        id=str(document.id),
        sourceKey=document.source_key,
        title=document.title,
        status=document.status,
        chunks=document.chunk_count,
    )


@router.post("/query", response_model=KnowledgeAnswer)
async def query_knowledge(
    payload: KnowledgeQueryRequest,
    request: Request,
    _admission: Annotated[None, Depends(enforce_ai_admission)],
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
) -> KnowledgeAnswer:
    try:
        result = await service.query(
            request_id=request.state.request_id,
            query=payload.query,
        )
    except Exception as exc:
        raise AppError("RAG_QUERY_FAILED", "知识检索暂时无法完成", status_code=503) from exc
    return KnowledgeAnswer(
        answer=result.answer,
        citations=[
            Citation(
                source=citation.source,
                chapter=citation.chapter,
                page=citation.page,
                snippet=citation.snippet,
            )
            for citation in result.citations
        ],
        retrieval=RetrievalDetails(
            originalQuery=result.retrieval.original_query,
            rewrittenQuery=result.retrieval.rewritten_query,
            retrievedDocuments=result.retrieval.retrieved_documents,
            rerankerEnabled=result.retrieval.reranker_enabled,
            vectorSearchMs=result.retrieval.vector_search_ms,
            rerankMs=result.retrieval.rerank_ms,
            retryCount=result.retrieval.retry_count,
            queryId=str(result.retrieval.query_id),
        ),
    )
