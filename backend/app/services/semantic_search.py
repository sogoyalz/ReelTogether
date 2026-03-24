from __future__ import annotations

import re

from app.models.movie import Movie

SYNONYMS = {
    "ai": {"artificial", "intelligence", "sci", "fi", "technology"},
    "sci-fi": {"science", "fiction", "space", "future"},
    "funny": {"comedy", "humor", "laughs"},
    "emotional": {"emotion", "heart", "moving"},
    "dark": {"crime", "gritty", "thriller"},
    "franchise": {"sequel", "universe", "brand"},
    "studio": {"company", "label", "banner"},
    "critics": {"reviews", "press", "reviewers"},
    "audience": {"fans", "viewers", "people"},
}


def semantic_query_score(
    *,
    query: str | None,
    movie: Movie,
    enrichment: dict,
    metadata: dict[str, str | None],
) -> float:
    if not query:
        return 0.0

    query_terms = _expand_terms(_tokenize(query))
    if not query_terms:
        return 0.0

    field_map = {
        "title": (movie.title, 3.5),
        "overview": (movie.overview or "", 2.2),
        "genres": (" ".join(movie.genres), 1.9),
        "franchise": (enrichment.get("franchise") or "", 1.9),
        "studios": (" ".join(enrichment.get("studios", [])), 1.6),
        "cast": (" ".join(enrichment.get("cast", [])), 1.3),
        "directors": (" ".join(enrichment.get("directors", [])), 1.3),
        "writers": (" ".join(enrichment.get("writers", [])), 1.0),
        "streaming": (" ".join(enrichment.get("streaming_on", [])), 0.6),
        "ratings": (" ".join(value for value in metadata.values() if isinstance(value, str)), 0.4),
    }

    score = 0.0
    for value, weight in field_map.values():
        tokens = _expand_terms(_tokenize(value))
        overlap = len(query_terms & tokens)
        if overlap:
            score += weight * (overlap / len(query_terms))
        if value and query.lower() in value.lower():
            score += weight * 0.55

    return round(score, 4)


def matches_semantic_query(
    *,
    query: str | None,
    movie: Movie,
    enrichment: dict,
    metadata: dict[str, str | None],
) -> bool:
    if not query:
        return True

    lowered = query.lower().strip()
    if not lowered:
        return True

    searchable = " ".join(
        [
            movie.title,
            movie.overview or "",
            " ".join(movie.genres),
            enrichment.get("franchise") or "",
            " ".join(enrichment.get("studios", [])),
            " ".join(enrichment.get("cast", [])),
            " ".join(enrichment.get("directors", [])),
            " ".join(enrichment.get("writers", [])),
        ]
    ).lower()
    if lowered in searchable:
        return True

    return semantic_query_score(query=query, movie=movie, enrichment=enrichment, metadata=metadata) >= 0.55


def _tokenize(value: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", value.lower()) if len(token) > 1}


def _expand_terms(tokens: set[str]) -> set[str]:
    expanded = set(tokens)
    for token in list(tokens):
        expanded.update(SYNONYMS.get(token, set()))
    return expanded
