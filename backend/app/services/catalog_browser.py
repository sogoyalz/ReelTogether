from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from sqlalchemy.orm import Session

from app.models.movie import Movie
from app.repositories import movies as movie_repository
from app.services.catalog_enrichment import get_enrichment
from app.services.omdb import fetch_movie_metadata


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
    candidates = movie_repository.list_movies(db)
    facets = _build_facets(candidates)
    filtered = [movie for movie in candidates if _matches(movie, filters)]
    sorted_movies = _sort_movies(filtered, filters.sort)
    total = len(sorted_movies)
    total_pages = max(1, ceil(total / filters.page_size)) if filters.page_size else 1
    page = min(max(filters.page, 1), total_pages)
    start = (page - 1) * filters.page_size
    end = start + filters.page_size
    return CatalogBrowseResult(
        movies=sorted_movies[start:end],
        total=total,
        page=page,
        page_size=filters.page_size,
        total_pages=total_pages,
        facets=facets,
    )


def _matches(movie: Movie, filters: CatalogBrowseFilters) -> bool:
    enrichment = get_enrichment(movie)
    metadata = fetch_movie_metadata(movie) or {}
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

    if filters.query and filters.query.lower() not in text:
        return False
    if filters.status and movie.status != filters.status:
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


def _sort_movies(movies: list[Movie], sort: str) -> list[Movie]:
    def rating(movie: Movie) -> float:
        return _parse_rating((fetch_movie_metadata(movie) or {}).get("imdb_rating"))

    def hype(movie: Movie) -> float:
        return _latest_hype(movie)

    def buzz(movie: Movie) -> float:
        analytics = _latest_analytics(movie)
        return analytics.buzz_score if analytics else 0.0

    def release(movie: Movie) -> float:
        return movie.release_date.toordinal()

    sorters = {
        "rating": lambda movie: (rating(movie), hype(movie), movie.title.lower()),
        "popularity": lambda movie: (movie.tmdb_popularity, hype(movie), movie.title.lower()),
        "release": lambda movie: (release(movie), hype(movie), movie.title.lower()),
        "buzz": lambda movie: (buzz(movie), hype(movie), movie.title.lower()),
        "title": lambda movie: (movie.title.lower(),),
        "hype": lambda movie: (hype(movie), movie.tmdb_popularity, movie.title.lower()),
    }
    sorter = sorters.get(sort, sorters["hype"])
    return sorted(movies, key=sorter, reverse=sort != "title")


def _build_facets(movies: list[Movie]) -> dict[str, list]:
    genres: set[str] = set()
    franchises: set[str] = set()
    studios: set[str] = set()
    streaming: set[str] = set()
    statuses: set[str] = set()
    years: set[int] = set()

    for movie in movies:
        enrichment = get_enrichment(movie)
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
