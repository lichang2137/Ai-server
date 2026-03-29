from __future__ import annotations

import re

from app.schemas import KnowledgeHit
from app.services.platform_registry import PlatformPackage


def _tokenize(query: str) -> list[str]:
    normalized = (query or "").lower()
    latin_tokens = [token for token in re.split(r"[\s/|,.;:!?()\[\]{}<>_-]+", normalized) if token]
    cjk_sequences = re.findall(r"[\u4e00-\u9fff]+", normalized)

    tokens: list[str] = []
    tokens.extend(token for token in latin_tokens if len(token) >= 2)
    for sequence in cjk_sequences:
        if len(sequence) >= 2:
            tokens.append(sequence)
        for size in (2, 3):
            if len(sequence) <= size:
                continue
            tokens.extend(sequence[index : index + size] for index in range(0, len(sequence) - size + 1))

    unique_tokens: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        unique_tokens.append(token)
    return unique_tokens


def _score(query: str, doc: dict, filters: dict | None = None) -> int:
    filters = filters or {}
    haystack = " ".join(
        [
            doc.get("title", ""),
            doc.get("content", ""),
            " ".join(doc.get("tags", [])),
            doc.get("category", ""),
            doc.get("section_slug", ""),
            doc.get("section_title", ""),
            doc.get("source_url", ""),
        ]
    ).lower()
    score = 0
    for token in _tokenize(query):
        if token in haystack:
            score += 4 if len(token) >= 4 else 2
    if filters.get("category") and filters["category"] in doc.get("category", ""):
        score += 2
    if filters.get("section_slug") and filters["section_slug"] == doc.get("section_slug"):
        score += 2
    return score


def search_platform_kb(package: PlatformPackage, query: str, filters: dict | None = None, limit: int = 3) -> list[KnowledgeHit]:
    filters = filters or {}
    candidates: list[tuple[int, dict]] = []
    for doc in package.knowledge_docs:
        score = _score(query, doc, filters)
        if score <= 0:
            continue
        candidates.append((score, doc))
    candidates.sort(key=lambda item: item[0], reverse=True)
    hits: list[KnowledgeHit] = []
    for _, doc in candidates[:limit]:
        hits.append(
            KnowledgeHit(
                title=doc.get("title", "Knowledge item"),
                source_url=doc.get("source_url", ""),
                updated_at=doc.get("updated_at"),
                summary=(doc.get("content", "") or "")[:220],
                tags=doc.get("tags", []),
            )
        )
    return hits
