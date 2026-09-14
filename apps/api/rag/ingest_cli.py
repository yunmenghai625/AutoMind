import argparse
import asyncio
import json
from pathlib import Path

from apps.api.core.config import get_settings
from apps.api.infrastructure.database import close_database, get_session_factory
from apps.api.infrastructure.knowledge_repository import PostgresKnowledgeRepository
from apps.api.rag.embeddings import build_embedding_provider
from apps.api.rag.ingestion import DocumentIngestionService


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index Markdown and PDF automotive documents")
    parser.add_argument("paths", nargs="+", type=Path, help="Files or directories to ingest")
    return parser.parse_args()


def _document_paths(paths: list[Path]) -> list[Path]:
    documents: list[Path] = []
    for path in paths:
        if path.is_dir():
            documents.extend(
                candidate
                for candidate in sorted(path.rglob("*"))
                if candidate.suffix.lower() in {".md", ".markdown", ".pdf"}
            )
        else:
            documents.append(path)
    return documents


async def _run(paths: list[Path]) -> int:
    settings = get_settings()
    provider = build_embedding_provider(settings)
    session_factory = get_session_factory(settings)
    indexed = []
    async with session_factory() as session:
        service = DocumentIngestionService(
            repository=PostgresKnowledgeRepository(session),
            embedding_provider=provider,
            batch_size=settings.embedding_batch_size,
        )
        for path in _document_paths(paths):
            document = await service.ingest_file(path)
            indexed.append(
                {
                    "source_key": document.source_key,
                    "title": document.title,
                    "chunks": document.chunk_count,
                    "status": document.status,
                }
            )
    print(json.dumps({"indexed": indexed}, ensure_ascii=False, indent=2))
    await close_database()
    return 0


def main() -> int:
    return asyncio.run(_run(_arguments().paths))


if __name__ == "__main__":
    raise SystemExit(main())
