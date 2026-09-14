import hashlib
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from apps.api.rag.chunking import ParsedBlock, chunk_blocks, parse_markdown
from apps.api.rag.embeddings import EmbeddingProvider
from apps.api.rag.entities import DocumentSummary
from apps.api.rag.repository import KnowledgeRepository

_INDEX_PIPELINE_VERSION = "automind-rag-index-v2"


class DocumentIngestionError(RuntimeError):
    pass


class DocumentIngestionService:
    def __init__(
        self,
        *,
        repository: KnowledgeRepository,
        embedding_provider: EmbeddingProvider,
        batch_size: int = 32,
    ) -> None:
        self._repository = repository
        self._embeddings = embedding_provider
        self._batch_size = batch_size

    async def ingest_markdown(
        self,
        *,
        source_key: str,
        title: str,
        text: str,
        description: str = "",
        source_uri: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DocumentSummary:
        return await self._ingest_blocks(
            source_key=source_key,
            title=title,
            description=description,
            source_type="markdown",
            source_uri=source_uri,
            raw_bytes=text.encode("utf-8"),
            blocks=parse_markdown(text),
            metadata=metadata or {},
        )

    async def ingest_file(
        self,
        path: Path,
        *,
        source_key: str | None = None,
        title: str | None = None,
        description: str = "",
    ) -> DocumentSummary:
        resolved = path.resolve()
        if not resolved.is_file():
            raise DocumentIngestionError(f"Document does not exist: {resolved}")
        suffix = resolved.suffix.lower()
        raw_bytes = resolved.read_bytes()
        if suffix in {".md", ".markdown"}:
            source_type = "markdown"
            blocks = parse_markdown(raw_bytes.decode("utf-8"))
        elif suffix == ".pdf":
            source_type = "pdf"
            reader = PdfReader(resolved)
            blocks = [
                ParsedBlock(None, page_number, page.extract_text() or "")
                for page_number, page in enumerate(reader.pages, start=1)
            ]
        else:
            raise DocumentIngestionError("Only Markdown and PDF files are supported")
        return await self._ingest_blocks(
            source_key=source_key or _source_key(resolved.stem),
            title=title or resolved.stem.replace("_", " "),
            description=description,
            source_type=source_type,
            source_uri=str(resolved),
            raw_bytes=raw_bytes,
            blocks=blocks,
            metadata={"filename": resolved.name},
        )

    async def _ingest_blocks(
        self,
        *,
        source_key: str,
        title: str,
        description: str,
        source_type: str,
        source_uri: str | None,
        raw_bytes: bytes,
        blocks: list[ParsedBlock],
        metadata: dict[str, Any],
    ) -> DocumentSummary:
        drafts = chunk_blocks(blocks)
        if not drafts:
            raise DocumentIngestionError("Document contains no indexable text")
        embedded = []
        for offset in range(0, len(drafts), self._batch_size):
            batch = drafts[offset : offset + self._batch_size]
            vectors = await self._embeddings.embed_batch([chunk.content for chunk in batch])
            if len(vectors) != len(batch):
                raise DocumentIngestionError("Embedding count does not match chunk count")
            embedded.extend(
                chunk.with_embedding(vector, self._embeddings.model_name)
                for chunk, vector in zip(batch, vectors, strict=True)
            )
        source_checksum = hashlib.sha256(raw_bytes).hexdigest()
        index_fingerprint = (
            f"{_INDEX_PIPELINE_VERSION}:{self._embeddings.model_name}:{self._embeddings.dimensions}"
        ).encode()
        index_checksum = hashlib.sha256(raw_bytes + b"\0" + index_fingerprint).hexdigest()
        return await self._repository.replace_document(
            source_key=source_key,
            title=title,
            description=description,
            source_type=source_type,
            source_uri=source_uri,
            checksum_sha256=index_checksum,
            metadata={
                **metadata,
                "source_checksum_sha256": source_checksum,
                "index_pipeline": _INDEX_PIPELINE_VERSION,
            },
            chunks=embedded,
        )


def _source_key(value: str) -> str:
    normalized = "-".join(value.lower().split())
    return "".join(char for char in normalized if char.isalnum() or char in {"-", "_"})[:160]
