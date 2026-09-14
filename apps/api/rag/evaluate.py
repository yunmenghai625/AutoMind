import argparse
import asyncio
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from apps.api.core.config import get_settings
from apps.api.infrastructure.database import close_database, get_session_factory
from apps.api.infrastructure.knowledge_repository import PostgresKnowledgeRepository
from apps.api.rag.embeddings import build_embedding_provider
from apps.api.rag.reranker import LocalOverlapReranker
from apps.api.rag.rewrite import RuleBasedQueryRewriter
from apps.api.rag.service import NO_EVIDENCE_ANSWER, KnowledgeService


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the repeatable AutoMind RAG gold set")
    parser.add_argument(
        "--gold",
        type=Path,
        default=Path("data/evaluation/gold_qa.jsonl"),
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def load_gold_set(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not 50 <= len(rows) <= 100:
        raise ValueError("Gold set must contain between 50 and 100 rows")
    return rows


async def evaluate(path: Path) -> dict[str, Any]:
    settings = get_settings()
    session_factory = get_session_factory(settings)
    provider = build_embedding_provider(settings)
    rows = load_gold_set(path)
    source_matches = 0
    answer_guard_matches = 0
    keyword_matches = 0
    details = []
    try:
        async with session_factory() as session:
            service = KnowledgeService(
                repository=PostgresKnowledgeRepository(session),
                embedding_provider=provider,
                reranker=LocalOverlapReranker(),
                rewriter=RuleBasedQueryRewriter(),
                top_k=settings.rag_top_k,
                confidence_threshold=settings.rag_confidence_threshold,
                max_retries=settings.rag_max_retries,
            )
            for row in rows:
                result = await service.query(
                    request_id=f"gold-{uuid4()}",
                    query=row["query"],
                )
                sources = {citation.source for citation in result.citations}
                source_ok = row.get("expected_source") in sources
                should_answer = bool(row.get("should_answer", True))
                answered = result.answer != NO_EVIDENCE_ANSWER
                guard_ok = answered == should_answer
                searchable = " ".join(
                    [result.answer, *(citation.snippet for citation in result.citations)]
                ).lower()
                keywords = [str(value).lower() for value in row.get("keywords", [])]
                keyword_ok = not keywords or any(keyword in searchable for keyword in keywords)
                source_matches += int(source_ok if should_answer else not sources)
                answer_guard_matches += int(guard_ok)
                keyword_matches += int(keyword_ok if should_answer else guard_ok)
                details.append(
                    {
                        "id": row["id"],
                        "source_ok": source_ok,
                        "guard_ok": guard_ok,
                        "keyword_ok": keyword_ok,
                        "retry_count": result.retrieval.retry_count,
                    }
                )
    finally:
        await close_database()
    total = len(rows)
    return {
        "dataset": str(path),
        "cases": total,
        "source_recall_at_3": round(source_matches / total, 4),
        "answer_guard_accuracy": round(answer_guard_matches / total, 4),
        "keyword_coverage": round(keyword_matches / total, 4),
        "details": details,
    }


def main() -> int:
    arguments = _arguments()
    report = asyncio.run(evaluate(arguments.gold))
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if arguments.output:
        arguments.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
