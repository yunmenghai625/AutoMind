from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from apps.api.rag.chunking import chunk_blocks, parse_markdown
from apps.api.rag.embeddings import HashingEmbeddingProvider
from apps.api.rag.entities import DocumentSummary, RetrievalHit
from apps.api.rag.ingestion import DocumentIngestionService
from apps.api.rag.reranker import LocalOverlapReranker
from apps.api.rag.rewrite import RuleBasedQueryRewriter
from apps.api.rag.service import NO_EVIDENCE_ANSWER, KnowledgeService


class InMemoryKnowledgeRepository:
    def __init__(self, searches: list[list[RetrievalHit]] | None = None) -> None:
        self.searches = searches or []
        self.search_queries: list[str] = []
        self.documents = []
        self.recorded_attempts: list[int] = []
        self.completed: dict | None = None
        self.failed: str | None = None
        self.query_id = uuid4()

    async def replace_document(self, **values):
        self.documents.append(values)
        return DocumentSummary(
            id=uuid4(),
            source_key=values["source_key"],
            title=values["title"],
            description=values["description"],
            status="indexed",
            chunk_count=len(values["chunks"]),
            updated_at=datetime.now(UTC),
        )

    async def create_query(self, *, request_id: str, original_query: str) -> UUID:
        return self.query_id

    async def hybrid_search(self, *, query_embedding, fts_query: str, limit: int):
        self.search_queries.append(fts_query)
        index = min(len(self.search_queries) - 1, max(0, len(self.searches) - 1))
        return self.searches[index] if self.searches else []

    async def record_hits(self, *, query_id, attempt: int, hits, selected_ids) -> None:
        self.recorded_attempts.append(attempt)

    async def complete_query(self, **values) -> None:
        self.completed = values

    async def fail_query(self, *, query_id, error_code: str) -> None:
        self.failed = error_code


def _hit(*, score: float = 0.8) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=uuid4(),
        document_id=uuid4(),
        source_key="vehicle-manual",
        title="Vehicle Manual",
        section="轮胎气压监测系统（TPMS）",
        page_number=217,
        content="胎压报警灯点亮时，应减速并安全停车，检查四条轮胎气压。",
        vector_score=score,
        text_score=score,
        hybrid_score=score,
    )


@pytest.mark.asyncio
async def test_hash_embedding_is_repeatable_and_schema_sized() -> None:
    provider = HashingEmbeddingProvider()
    first, second = await provider.embed_batch(["胎压 TPMS", "胎压 TPMS"])

    assert first == second
    assert len(first) == 384
    assert sum(value * value for value in first) == pytest.approx(1.0)


def test_markdown_parser_preserves_section_page_and_overlap() -> None:
    blocks = parse_markdown(
        "# 车辆手册\n<!-- page: 217 -->\n## TPMS\n" + "胎压报警后应停车检查。" * 80
    )
    chunks = chunk_blocks(blocks, max_chars=180, overlap_chars=30)

    assert len(chunks) > 1
    assert all(chunk.section == "TPMS" for chunk in chunks)
    assert all(chunk.page_number == 217 for chunk in chunks)
    assert chunks[0].embedding is None
    assert "胎压" in chunks[0].fts_text


@pytest.mark.asyncio
async def test_ingestion_batches_embeddings_and_keeps_citation_metadata() -> None:
    repository = InMemoryKnowledgeRepository()
    service = DocumentIngestionService(
        repository=repository,
        embedding_provider=HashingEmbeddingProvider(),
        batch_size=2,
    )

    result = await service.ingest_markdown(
        source_key="manual",
        title="车辆手册",
        text="<!-- page: 12 -->\n## 雨刮器\n雨刮片出现条纹时需要检查并更换。",
    )

    saved = repository.documents[0]
    assert result.status == "indexed"
    assert saved["chunks"][0].page_number == 12
    assert saved["chunks"][0].section == "雨刮器"
    assert len(saved["chunks"][0].embedding) == 384


@pytest.mark.asyncio
async def test_query_returns_grounded_answer_and_precise_citation() -> None:
    repository = InMemoryKnowledgeRepository(searches=[[_hit()]])
    service = KnowledgeService(
        repository=repository,
        embedding_provider=HashingEmbeddingProvider(),
        reranker=LocalOverlapReranker(),
        rewriter=RuleBasedQueryRewriter(),
        top_k=5,
        confidence_threshold=0.2,
        max_retries=2,
    )

    result = await service.query(request_id="rag-grounded", query="胎压报警怎么办")

    assert result.answer.startswith("根据《Vehicle Manual》")
    assert result.citations[0].chapter == "轮胎气压监测系统（TPMS）"
    assert result.citations[0].page == 217
    assert repository.recorded_attempts == [0]
    assert repository.completed and repository.completed["status"] == "success"


@pytest.mark.asyncio
async def test_low_confidence_rewrites_at_most_twice_then_refuses() -> None:
    repository = InMemoryKnowledgeRepository(searches=[[], [], []])
    service = KnowledgeService(
        repository=repository,
        embedding_provider=HashingEmbeddingProvider(),
        reranker=LocalOverlapReranker(),
        rewriter=RuleBasedQueryRewriter(),
        top_k=5,
        confidence_threshold=0.9,
        max_retries=99,
    )

    result = await service.query(request_id="rag-empty", query="胎压报警怎么办")

    assert result.answer == NO_EVIDENCE_ANSWER
    assert result.citations == []
    assert repository.recorded_attempts == [0, 1, 2]
    assert result.retrieval.retry_count == 2
    assert "安全注意事项" in result.retrieval.rewritten_query
    assert repository.completed and repository.completed["status"] == "no_evidence"
