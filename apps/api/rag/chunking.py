import re
from dataclasses import dataclass

from apps.api.rag.entities import ChunkDraft
from apps.api.rag.text import to_fts_text

_PAGE_MARKER = re.compile(r"<!--\s*page\s*:\s*(\d+)\s*-->", re.IGNORECASE)
_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$")


@dataclass(frozen=True, slots=True)
class ParsedBlock:
    section: str | None
    page_number: int | None
    text: str


def parse_markdown(text: str) -> list[ParsedBlock]:
    blocks: list[ParsedBlock] = []
    section: str | None = None
    page_number: int | None = None
    buffer: list[str] = []

    def flush() -> None:
        content = "\n".join(buffer).strip()
        if content:
            blocks.append(ParsedBlock(section, page_number, content))
        buffer.clear()

    for line in text.splitlines():
        page_match = _PAGE_MARKER.fullmatch(line.strip())
        if page_match:
            flush()
            page_number = int(page_match.group(1))
            continue
        heading_match = _HEADING.match(line)
        if heading_match:
            flush()
            section = heading_match.group(1).strip()
            continue
        if line.strip() or buffer:
            buffer.append(line)
    flush()
    return blocks


def chunk_blocks(
    blocks: list[ParsedBlock], *, max_chars: int = 700, overlap_chars: int = 100
) -> list[ChunkDraft]:
    if max_chars < 100 or not 0 <= overlap_chars < max_chars:
        raise ValueError("Invalid chunk size or overlap")
    drafts: list[ChunkDraft] = []
    for block in blocks:
        content = " ".join(block.text.split())
        start = 0
        while start < len(content):
            stop = min(start + max_chars, len(content))
            if stop < len(content):
                boundary = content.rfind("。", start + max_chars // 2, stop)
                if boundary > start:
                    stop = boundary + 1
            piece = content[start:stop].strip()
            if piece:
                drafts.append(
                    ChunkDraft(
                        ordinal=len(drafts),
                        section=block.section,
                        page_number=block.page_number,
                        content=piece,
                        fts_text=to_fts_text(piece),
                        token_count=max(1, len(piece) // 2),
                        metadata={},
                    )
                )
            if stop >= len(content):
                break
            start = max(stop - overlap_chars, start + 1)
    return drafts
