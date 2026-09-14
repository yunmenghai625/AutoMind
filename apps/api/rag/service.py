from time import perf_counter

from apps.api.rag.embeddings import EmbeddingProvider
from apps.api.rag.entities import (
    CitationData,
    KnowledgeResult,
    RetrievalHit,
    RetrievalMetrics,
)
from apps.api.rag.repository import KnowledgeRepository
from apps.api.rag.reranker import Reranker
from apps.api.rag.rewrite import RuleBasedQueryRewriter

NO_EVIDENCE_ANSWER = "未检索到足够可靠的资料，暂不提供推断性答案。"


class KnowledgeService:
    def __init__(
        self,
        *,
        repository: KnowledgeRepository,
        embedding_provider: EmbeddingProvider,
        reranker: Reranker,
        rewriter: RuleBasedQueryRewriter,
        top_k: int,
        confidence_threshold: float,
        max_retries: int,
    ) -> None:
        self._repository = repository
        self._embeddings = embedding_provider
        self._reranker = reranker
        self._rewriter = rewriter
        self._top_k = top_k
        self._threshold = confidence_threshold
        self._max_retries = min(max_retries, 2)

    async def query(self, *, request_id: str, query: str) -> KnowledgeResult:
        query_id = await self._repository.create_query(request_id=request_id, original_query=query)
        current_query = query
        search_ms = 0
        rerank_ms = 0
        retry_count = 0
        final_hits: list[RetrievalHit] = []
        best_observed_score: float | None = None
        try:
            for attempt in range(self._max_retries + 1):
                search_started = perf_counter()
                query_vector = (await self._embeddings.embed_batch([current_query]))[0]
                hits = await self._repository.hybrid_search(
                    query_embedding=query_vector,
                    fts_query=current_query,
                    limit=max(20, self._top_k * 4),
                )
                search_ms += round((perf_counter() - search_started) * 1000)

                rerank_started = perf_counter()
                reranked = await self._reranker.rerank(current_query, hits)
                rerank_ms += round((perf_counter() - rerank_started) * 1000)
                top_hits = reranked[: self._top_k]
                top_score = top_hits[0].rerank_score if top_hits else None
                if top_score is not None:
                    best_observed_score = max(best_observed_score or 0.0, top_score)
                confident = top_score is not None and top_score >= self._threshold
                selected = {hit.chunk_id for hit in top_hits[:3]} if confident else set()
                await self._repository.record_hits(
                    query_id=query_id,
                    attempt=attempt,
                    hits=reranked,
                    selected_ids=selected,
                )
                if confident:
                    final_hits = top_hits
                    break
                if attempt >= self._max_retries:
                    break
                rewritten = self._rewriter.rewrite(query, attempt + 1)
                if rewritten == current_query:
                    break
                current_query = rewritten
                retry_count = attempt + 1

            citations = _citations(final_hits[:3])
            answer = _grounded_answer(final_hits[0]) if final_hits else NO_EVIDENCE_ANSWER
            top_score = final_hits[0].rerank_score if final_hits else best_observed_score
            retrieved_documents = len({hit.document_id for hit in final_hits})
            await self._repository.complete_query(
                query_id=query_id,
                rewritten_query=current_query,
                answer_text=answer,
                status="success" if final_hits else "no_evidence",
                retry_count=retry_count,
                retrieved_count=retrieved_documents,
                low_confidence=not final_hits,
                top_score=top_score,
                vector_search_ms=search_ms,
                rerank_ms=rerank_ms,
            )
            return KnowledgeResult(
                answer=answer,
                citations=citations,
                retrieval=RetrievalMetrics(
                    original_query=query,
                    rewritten_query=current_query,
                    retrieved_documents=retrieved_documents,
                    reranker_enabled=self._reranker.enabled,
                    vector_search_ms=search_ms,
                    rerank_ms=rerank_ms,
                    retry_count=retry_count,
                    query_id=query_id,
                ),
            )
        except Exception as exc:
            await self._repository.fail_query(query_id=query_id, error_code=type(exc).__name__)
            raise


def _citations(hits: list[RetrievalHit]) -> list[CitationData]:
    return [
        CitationData(
            source=hit.title,
            chapter=hit.section,
            page=hit.page_number,
            snippet=_snippet(hit.content),
        )
        for hit in hits
    ]


def _grounded_answer(hit: RetrievalHit) -> str:
    location = f"《{hit.title}》"
    if hit.section:
        location += f"“{hit.section}”章节"
    if hit.page_number:
        location += f"第 {hit.page_number} 页"
    return f"根据{location}：{_snippet(hit.content, limit=460)}"


def _snippet(text: str, *, limit: int = 280) -> str:
    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else normalized[: limit - 1].rstrip() + "…"
