from typing import Protocol

from apps.api.rag.entities import RetrievalHit
from apps.api.rag.text import lexical_tokens

_QUERY_ALIASES = {
    "后段": "高电量 降低功率",
    "冬季": "低温 电池预热 续航余量",
    "存放": "停放 长期停放",
    "两周": "超过两周 长期停放",
}


class Reranker(Protocol):
    @property
    def enabled(self) -> bool: ...

    async def rerank(self, query: str, hits: list[RetrievalHit]) -> list[RetrievalHit]: ...


class LocalOverlapReranker:
    @property
    def enabled(self) -> bool:
        return True

    async def rerank(self, query: str, hits: list[RetrievalHit]) -> list[RetrievalHit]:
        query_tokens = set(lexical_tokens(query))
        alias_text = " ".join(value for key, value in _QUERY_ALIASES.items() if key in query)
        alias_tokens = set(lexical_tokens(alias_text))
        scored: list[RetrievalHit] = []
        for hit in hits:
            content_tokens = set(lexical_tokens(hit.content))
            direct_overlap = len(query_tokens & content_tokens) / max(1, len(query_tokens))
            alias_overlap = len(alias_tokens & content_tokens) / max(1, len(alias_tokens))
            overlap = max(direct_overlap, alias_overlap * 0.8)
            score = max(0.0, min(1.0, hit.hybrid_score * 0.65 + overlap * 0.35))
            scored.append(hit.with_rerank_score(score))
        return sorted(scored, key=lambda item: item.rerank_score or 0, reverse=True)
