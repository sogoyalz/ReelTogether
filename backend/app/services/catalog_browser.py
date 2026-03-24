from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from sqlalchemy.orm import Session

from app.models.movie import Movie
from app.repositories import movies as movie_repository
from app.services.catalog_enrichment import get_enrichment
from app.services.omdb import fetch_movie_metadata
from app.services.cache import TTLCache
from app.services.semantic_search import matches_semantic_query, semantic_query_score


_BROWSE_CACHE: TTLCache[CatalogBrowseResult] | None = None


@dataclass
class CatalogBrowseFilters:
    query: str | None = None
    status: str | None = None
    genre: str | None = None
    studio: str | None = None
    franchise: str | None = None
    streaming: str | None = None
    year: int | None = None
    min_rating: float | None = None
    min_hype: float | None = None
    min_popularity: float | None = None
    sort: str = "hype"
    page: int = 1
    page_size: int = 24


@dataclass
class CatalogBrowseResult:
    movies: list[Movie]
    total: int
    page: int
    page_size: int
    total_pages: int
    facets: dict[str, list]


def browse_catalog(db: Session, filters: CatalogBrowseFilters) -> CatalogBrowseResult:
    global _BROWSE_CACHE
    if _BROWSE_CACHE is None:
        _BROWSE_CACHE = TTLCache(ttl_seconds=45)

    cache_key = "|".join(
        [
            filters.query or "",
            filters.status or "",
            filters.genre or "",
            filters.studio or "",
            filters.franchise or "",
            filters.streaming or "",
            str(filters.year or ""),
            str(filters.min_rating or ""),
            str(filters.min_hype or ""),
            str(filters.min_popularity or ""),
            filters.sort,
            str(filters.page),
            str(filters.page_size),
        ]
    )

    return _BROWSE_CACHE.get_or_set(cache_key, lambda: _build_browse_result(db, filters))


def _build_browse_result(db: Session, filters: CatalogBrowseFilters) -> CatalogBrowseResult:
    candidates = movie_repository.list_movies(db)
    prepared = [_prepare_movie(movie) for movie in candidates]
    facets = _build_facets(prepared)
    filtered = [item for item in prepared if _matches(item, filters)]
    sorted_movies = _sort_movies(filtered, filters.sort)
    total = len(sorted_movies)
    total_pages = max(1, ceil(total / filters.page_size)) if filters.page_size else 1
    page = min(max(filters.page, 1), total_pages)
    start = (page - 1) * filters.page_size
    end = start + filters.page_size
    return CatalogBrowseResult(
        movies=[item["movie"] for item in sorted_movies[start:end]],
        total=total,
        page=page,
        page_size=filters.page_size,
        total_pages=total_pages,
        facets=facets,
    )


def _prepare_movie(movie: Movie) -> dict:
    enrichment = get_enrichment(movie)
    metadata = fetch_movie_metadata(movie) or {}
    return {
        "movie": movie,
        "enrichment": enrichment,
        "metadata": metadata,
        "analytics": _latest_analytics(movie),
        "semantic_score": 0.0,
    }


def _matches(item: dict, filters: CatalogBrowseFilters) -> bool:
    movie: Movie = item["movie"]
    enrichment = item["enrichment"]
    metadata = item["metadata"]
    item["semantic_score"] = semantic_query_score(
        query=filters.query,
        movie=movie,
        enrichment=enrichment,
        metadata=metadata,
    )

    if filters.query and not matches_semantic_query(
        query=filters.query,
        movie=movie,
        enrichment=enrichment,
        metadata=metadata,
    ):
        return False
    if filters.status:
        if filters.status == "future":
            if movie.status == "released":
                return False
        elif movie.status != filters.status:
            return False
    if filters.genre and filters.genre not in movie.genres:
        return False
    if filters.studio and filters.studio not in enrichment.get("studios", []):
        return False
    if filters.franchise and enrichment.get("franchise") != filters.franchise:
        return False
    if filters.streaming and filters.streaming not in enrichment.get("streaming_on", []):
        return False
    if filters.year and movie.release_date.year != filters.year:
        return False
    if filters.min_rating and _parse_rating(metadata.get("imdb_rating")) < filters.min_rating:
        return False
    if filters.min_hype and _latest_hype(movie) < filters.min_hype:
        return False
    if filters.min_popularity and movie.tmdb_popularity < filters.min_popularity:
        return False
    return True


def _sort_movies(items: list[dict], sort: str) -> list[dict]:
    def rating(item: dict) -> float:
        return _parse_rating(item["metadata"].get("imdb_rating"))

    def hype(item: dict) -> float:
        analytics = item["analytics"]
        return analytics.hype_score if analytics else 0.0

    def buzz(item: dict) -> float:
        analytics = item["analytics"]
        return analytics.buzz_score if analytics else 0.0

    def release(item: dict) -> float:
        movie: Movie = item["movie"]
        return movie.release_date.toordinal()

    def semantic(item: dict) -> float:
        return item.get("semantic_score", 0.0)

    sorters = {
        "rating": lambda item: (semantic(item), rating(item), hype(item), item["movie"].title.lower()),
        "popularity": lambda item: (semantic(item), item["movie"].tmdb_popularity, hype(item), item["movie"].title.lower()),
        "release": lambda item: (semantic(item), release(item), hype(item), item["movie"].title.lower()),
        "buzz": lambda item: (semantic(item), buzz(item), hype(item), item["movie"].title.lower()),
        "title": lambda item: (-semantic(item), item["movie"].title.lower()),
        "hype": lambda item: (semantic(item), hype(item), item["movie"].tmdb_popularity, item["movie"].title.lower()),
    }
    sorter = sorters.get(sort, sorters["hype"])
    return sorted(items, key=sorter, reverse=sort != "title")


def _build_facets(items: list[dict]) -> dict[str, list]:
    genres: set[str] = set()
    franchises: set[str] = set()
    studios: set[str] = set()
    streaming: set[str] = set()
    statuses: set[str] = set()
    years: set[int] = set()

    for item in items:
        movie: Movie = item["movie"]
        enrichment = item["enrichment"]
        genres.update(movie.genres)
        statuses.add(movie.status)
        years.add(movie.release_date.year)
        if enrichment.get("franchise"):
            franchises.add(enrichment["franchise"])
        studios.update(enrichment.get("studios", []))
        streaming.update(enrichment.get("streaming_on", []))

    return {
        "genres": sorted(genres),
        "franchises": sorted(franchises),
        "studios": sorted(studios),
        "streaming": sorted(streaming),
        "statuses": sorted(statuses),
        "years": sorted(years, reverse=True),
    }


def clear_browse_cache() -> None:
    if _BROWSE_CACHE is not None:
        _BROWSE_CACHE.clear()


def _latest_analytics(movie: Movie):
    return next(
        (snapshot for snapshot in movie.analytics_snapshots if snapshot.snapshot_label == "latest"),
        None,
    )


def _latest_hype(movie: Movie) -> float:
    analytics = _latest_analytics(movie)
    return analytics.hype_score if analytics else 0.0


def _parse_rating(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0
