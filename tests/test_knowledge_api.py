from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.api.dependencies import (
    get_admin_identity,
    get_document_ingestion_service,
    get_knowledge_repository,
    get_knowledge_service,
)
from apps.api.auth.service import AuthIdentity
from apps.api.rag.entities import (
    CitationData,
    DocumentSummary,
    KnowledgeResult,
    RetrievalMetrics,
)


class FakeKnowledgeRepository:
    async def list_documents(self):
        return [
            DocumentSummary(
                id=uuid4(),
                source_key="vehicle-manual",
                title="Vehicle Manual",
                description="车辆用户手册",
                status="indexed",
                chunk_count=8,
                updated_at=datetime(2026, 9, 12, tzinfo=UTC),
            )
        ]


class FakeIngestionService:
    async def ingest_markdown(self, **values):
        return DocumentSummary(
            id=uuid4(),
            source_key=values["source_key"],
            title=values["title"],
            description=values["description"],
            status="indexed",
            chunk_count=2,
            updated_at=datetime.now(UTC),
        )


class FakeKnowledgeService:
    async def query(self, *, request_id: str, query: str):
        return KnowledgeResult(
            answer="根据《Vehicle Manual》“TPMS”章节第 217 页：应安全停车检查胎压。",
            citations=[
                CitationData(
                    source="Vehicle Manual",
                    chapter="TPMS",
                    page=217,
                    snippet="应安全停车检查胎压。",
                )
            ],
            retrieval=RetrievalMetrics(
                original_query=query,
                rewritten_query=query,
                retrieved_documents=1,
                reranker_enabled=True,
                vector_search_ms=4,
                rerank_ms=1,
                retry_count=0,
                query_id=uuid4(),
            ),
        )


def _override_knowledge_dependencies(client: TestClient) -> None:
    client.app.dependency_overrides[get_knowledge_repository] = FakeKnowledgeRepository
    client.app.dependency_overrides[get_document_ingestion_service] = FakeIngestionService
    client.app.dependency_overrides[get_knowledge_service] = FakeKnowledgeService


def test_list_knowledge_sources_matches_frontend_contract(client: TestClient) -> None:
    _override_knowledge_dependencies(client)

    response = client.get("/api/v1/knowledge/sources")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "vehicle-manual",
            "title": "Vehicle Manual",
            "description": "车辆用户手册",
            "documents": 1,
            "status": "indexed",
            "updatedAt": "2026-09-12",
        }
    ]


def test_query_knowledge_returns_traceable_citation(client: TestClient) -> None:
    _override_knowledge_dependencies(client)

    response = client.post(
        "/api/v1/knowledge/query",
        headers={"X-Request-ID": "knowledge-api"},
        json={"query": "胎压报警怎么办"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["citations"][0] == {
        "source": "Vehicle Manual",
        "chapter": "TPMS",
        "page": 217,
        "snippet": "应安全停车检查胎压。",
    }
    assert payload["retrieval"]["queryId"]
    assert payload["retrieval"]["retryCount"] == 0


def test_ingest_markdown_endpoint_returns_index_summary(client: TestClient) -> None:
    _override_knowledge_dependencies(client)
    client.app.dependency_overrides[get_admin_identity] = lambda: AuthIdentity(
        kind="registered",
        user_id=uuid4(),
        role="admin",
    )

    response = client.post(
        "/api/v1/knowledge/documents/ingest",
        json={
            "sourceKey": "manual-2026",
            "title": "车辆手册",
            "content": "<!-- page: 1 -->\n## 安全\n请遵循车辆安全说明。",
        },
    )

    assert response.status_code == 200
    assert response.json()["chunks"] == 2
    assert response.json()["status"] == "indexed"


def test_ingest_markdown_endpoint_rejects_guest(client: TestClient) -> None:
    _override_knowledge_dependencies(client)

    response = client.post(
        "/api/v1/knowledge/documents/ingest",
        json={
            "sourceKey": "unsafe-public-write",
            "title": "不应写入",
            "content": "未认证用户不能修改线上知识库。",
        },
    )

    assert response.status_code == 401
