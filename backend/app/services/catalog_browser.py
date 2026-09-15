from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite

from sqlalchemy.orm import Session

from app.models.movie import Movie
from app.services.movie_data import derive_canonical_status
from app.repositories import movies as movie_repository
from app.services.catalog_enrichment import get_enrichment
from app.services.cache import TTLCache
from app.services.semantic_search import matches_semantic_query, semantic_query_score


_BROWSE_CACHE: TTLCache[CatalogBrowseResult] | None = None


@dataclass
class CatalogBrowseFilters:
    query: str | None = None
    status: str | None = None
    genre: str | None = None
    studio: str | None = None
    director: str | None = None
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
    if db.get_bind().dialect.name == "sqlite":
        from app.services.catalog_sql import browse_sqlite
        return browse_sqlite(db, filters)
    # Compatibility path for other dialects; ORM objects are never cached globally.
    return _build_browse_result(db, filters)


def _build_browse_result(db: Session, filters: CatalogBrowseFilters) -> CatalogBrowseResult:
    candidates = movie_repository.list_summary_movies(db)
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
    # NOTE: OMDB metadata is intentionally excluded here — it requires one HTTP call per movie
    # and is only needed on detail/compare pages, not browse lists. The browse cache also
    # cannot include live network I/O on every cache miss without making the first load
    # several minutes long for a large catalog.
    return {
        "movie": movie,
        "enrichment": enrichment,
        "metadata": movie.provider_metadata or {},
        "analytics": _latest_analytics(movie),
        "semantic_score": 0.0,
    }


def _matches(item: dict, filters: CatalogBrowseFilters) -> bool:
    movie: Movie = item["movie"]
    enrichment = item["enrichment"]
    metadata = item["metadata"]
    if filters.query:
        text = " ".join(
            [
                movie.title,
                movie.overview or "",
                enrichment.get("franchise") or "",
                " ".join(movie.genres),
                " ".join(enrichment.get("studios", [])),
                " ".join(enrichment.get("cast", [])),
                " ".join(enrichment.get("directors", [])),
                " ".join(enrichment.get("writers", [])),
            ]
        ).lower()

        if filters.query.lower() not in text:
            return False
    if filters.status:
        if filters.status == "future":
            if derive_canonical_status(movie) == "released":
                return False
        elif derive_canonical_status(movie) != filters.status:
            return False
    if filters.genre and filters.genre not in movie.genres:
        return False
    if filters.studio and filters.studio not in enrichment.get("studios", []):
        return False
    if filters.director and filters.director not in enrichment.get("directors", []):
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

    sorters = {
        "rating": lambda item: (rating(item), hype(item), item["movie"].title.lower()),
        "popularity": lambda item: (item["movie"].tmdb_popularity, hype(item), item["movie"].title.lower()),
        "release": lambda item: (release(item), hype(item), item["movie"].title.lower()),
        "buzz": lambda item: (buzz(item), hype(item), item["movie"].title.lower()),
        "title": lambda item: (item["movie"].title.lower(),),
        "hype": lambda item: (hype(item), item["movie"].tmdb_popularity, item["movie"].title.lower()),
    }
    if sort == "release_asc":
        return sorted(items, key=lambda item: (release(item), item["movie"].id))
    if sort == "none":
        return sorted(items, key=lambda item: item["movie"].id)
    sorter = sorters.get(sort, sorters["hype"])
    return sorted(items, key=sorter, reverse=sort != "title")


def _build_facets(items: list[dict]) -> dict[str, list]:
    genres: set[str] = set()
    franchises: set[str] = set()
    studios: set[str] = set()
    directors: set[str] = set()
    streaming: set[str] = set()
    statuses: set[str] = set()
    years: set[int] = set()

    for item in items:
        movie: Movie = item["movie"]
        enrichment = item["enrichment"]
        genres.update(movie.genres)
        statuses.add(derive_canonical_status(movie))
        years.add(movie.release_date.year)
        if enrichment.get("franchise"):
            franchises.add(enrichment["franchise"])
        studios.update(enrichment.get("studios", []))
        directors.update(enrichment.get("directors", []))
        streaming.update(enrichment.get("streaming_on", []))

    return {
        "genres": sorted(genres),
        "franchises": sorted(franchises),
        "studios": sorted(studios),
        "directors": sorted(directors),
        "streaming": sorted(streaming),
        "statuses": sorted(statuses),
        "years": sorted(years, reverse=True),
    }


def clear_browse_cache() -> None:
    if _BROWSE_CACHE is not None:
        _BROWSE_CACHE.clear()


def _latest_analytics(movie: Movie):
    return movie_repository.latest_analytics(movie)


def _latest_hype(movie: Movie) -> float:
    analytics = _latest_analytics(movie)
    return analytics.hype_score if analytics else 0.0


def _parse_rating(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        rating = float(value)
        return rating if isfinite(rating) and 0 <= rating <= 10 else 0.0
    except (ValueError, TypeError):
        return 0.0
