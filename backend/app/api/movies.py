"""Movie API endpoints — professional, parallel, and cache-aware."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from app.api.admin import _authorize_admin
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.schemas.analytics import RefreshAnalyticsResponse
from app.schemas.movie import CatalogFacets, MovieDetail, MovieSummary, PaginatedMovieSummaries
from app.db.session import get_db
from app.models.movie import Movie
from app.repositories import movies as movie_repository
from app.services.catalog_browser import CatalogBrowseFilters, browse_catalog, clear_browse_cache
from app.services.cache import TTLCache
from app.services.catalog_enrichment import get_enrichment
from app.services.movie_data import build_movie_data_contract
from app.services.provider_metadata import normalize_metadata
from app.services.omdb import fetch_movie_metadata
from app.services.tmdb import sync_tmdb_catalog
from app.services.wikidata import fetch_movie_wikidata
from app.services.wikipedia import fetch_movie_wikipedia

logger = logging.getLogger(__name__)

router = APIRouter()
_DETAIL_ENRICHMENT_CACHE: TTLCache[dict] = TTLCache(ttl_seconds=1800)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _latest_analytics(movie: Movie):
    return movie_repository.latest_analytics(movie)


def _analytics_payload(movie: Movie) -> dict:
    analytics = _latest_analytics(movie)
    if analytics is None:
        return {
            "trailer_url": None,
            "youtube_views": 0,
            "youtube_likes": 0,
            "youtube_comments": 0,
            "google_trends_score": 0.0,
            "x_mentions": 0,
            "reddit_mentions": 0,
            "sentiment_score": 0.0,
            "buzz_score": 0.0,
            "hype_score": 0.0,
            "predicted_opening_weekend_usd": 0.0,
            "predicted_domestic_total_usd": 0.0,
        }

    return {
        "trailer_url": analytics.trailer_url,
        "youtube_views": analytics.youtube_views,
        "youtube_likes": analytics.youtube_likes,
        "youtube_comments": analytics.youtube_comments,
        "google_trends_score": analytics.google_trends_score,
        "x_mentions": analytics.x_mentions,
        "reddit_mentions": analytics.reddit_mentions,
        "sentiment_score": analytics.sentiment_score,
        "buzz_score": analytics.buzz_score,
        "hype_score": analytics.hype_score,
        "predicted_opening_weekend_usd": analytics.predicted_opening_weekend_usd,
        "predicted_domestic_total_usd": analytics.predicted_domestic_total_usd,
    }


def _serialize_summary_fast(movie: Movie) -> MovieSummary:
    """Fast list-view serialization — skips live OMDB HTTP call (OMDB used on detail only)."""
    analytics = _analytics_payload(movie)
    enrichment = get_enrichment(movie)
    metadata = normalize_metadata(movie.provider_metadata)

    return MovieSummary(
        id=movie.id,
        tmdb_id=movie.tmdb_id,
        slug=movie.slug,
        title=movie.title,
        release_date=movie.release_date,
        **{key: value for key, value in build_movie_data_contract(movie, analytics=_latest_analytics(movie), enrichment=enrichment, omdb_metadata=metadata).items() if key in MovieSummary.model_fields},
        poster_url=movie.poster_url,
        backdrop_url=movie.backdrop_url,
        overview=movie.overview,
        genres=movie.genres,
        tmdb_popularity=movie.tmdb_popularity,
        buzz_score=analytics["buzz_score"],
        hype_score=analytics["hype_score"],
        franchise=enrichment["franchise"],
        studios=enrichment["studios"],
        streaming_on=enrichment["streaming_on"],
        directors=enrichment["directors"],
        cast=enrichment["cast"],
        imdb_rating=metadata.get("imdb_rating"),
        rated=metadata.get("rated"),
        runtime=metadata.get("runtime"),
        rotten_tomatoes=metadata.get("rotten_tomatoes"),
        logo_url=enrichment.get("logo_url"),
    )


def _serialize_summary_full(movie: Movie) -> MovieSummary:
    """Full serialization with OMDB data. Used for search results."""
    analytics = _analytics_payload(movie)
    enrichment = get_enrichment(movie)
    metadata = normalize_metadata(movie.provider_metadata)
    omdb_metadata = normalize_metadata(fetch_movie_metadata(movie))

    return MovieSummary(
        id=movie.id,
        tmdb_id=movie.tmdb_id,
        slug=movie.slug,
        title=movie.title,
        release_date=movie.release_date,
        **{key: value for key, value in build_movie_data_contract(movie, analytics=_latest_analytics(movie), enrichment=enrichment, omdb_metadata=metadata).items() if key in MovieSummary.model_fields},
        poster_url=movie.poster_url,
        backdrop_url=movie.backdrop_url,
        overview=movie.overview,
        genres=movie.genres,
        tmdb_popularity=movie.tmdb_popularity,
        buzz_score=analytics["buzz_score"],
        hype_score=analytics["hype_score"],
        franchise=enrichment["franchise"],
        studios=enrichment["studios"],
        streaming_on=enrichment["streaming_on"],
        directors=enrichment["directors"],
        cast=enrichment["cast"],
        imdb_rating=omdb_metadata.get("imdb_rating"),
        rated=omdb_metadata.get("rated"),
        runtime=omdb_metadata.get("runtime"),
        rotten_tomatoes=omdb_metadata.get("rotten_tomatoes"),
        logo_url=enrichment.get("logo_url"),
    )


def _serialize_detail(movie: Movie) -> MovieDetail:
    analytics = _analytics_payload(movie)
    enrichment = get_enrichment(movie)
    metadata = normalize_metadata(movie.provider_metadata)
    omdb_metadata, wikipedia, wikidata = _fetch_detail_enrichment(movie)
    omdb_metadata = normalize_metadata(omdb_metadata)

    summary = _serialize_summary_fast(movie)

    detail = MovieDetail(
        **summary.model_dump(
            exclude={"imdb_rating", "rated", "runtime", "rotten_tomatoes"},
        ),
        # Override OMDB fields now that we have them
        imdb_rating=omdb_metadata.get("imdb_rating"),
        rated=omdb_metadata.get("rated"),
        runtime=omdb_metadata.get("runtime"),
        rotten_tomatoes=omdb_metadata.get("rotten_tomatoes"),
        # Detail-only fields
        trailer_url=analytics["trailer_url"],
        trailer_views=analytics["youtube_views"],
        social_mentions=analytics["x_mentions"] + analytics["reddit_mentions"],
        google_trends_score=analytics["google_trends_score"],
        sentiment_score=analytics["sentiment_score"],
        predicted_opening_weekend_usd=analytics["predicted_opening_weekend_usd"],
        predicted_domestic_total_usd=analytics["predicted_domestic_total_usd"],
        imdb_id=omdb_metadata.get("imdb_id"),
        box_office=omdb_metadata.get("box_office"),
        awards=omdb_metadata.get("awards"),
        metascore=omdb_metadata.get("metascore"),
        imdb_votes=omdb_metadata.get("imdb_votes"),
        omdb_poster_url=omdb_metadata.get("omdb_poster_url"),
        writers=enrichment["writers"],
        trailer_embed_url=enrichment["trailer_embed_url"],
        box_office_history=enrichment["box_office_history"],
        backdrops=enrichment.get("backdrops", []),
        wikipedia_summary=wikipedia.get("summary"),
        wikipedia_url=wikipedia.get("url"),
        wikipedia_categories=wikipedia.get("categories", []),
        wikidata_id=wikidata.get("id"),
        wikidata_url=wikidata.get("url"),
        wikidata_label=wikidata.get("label"),
        wikidata_description=wikidata.get("description"),
        wikidata_instance_of=wikidata.get("instance_of", []),
        wikidata_genres=wikidata.get("genres", []),
        wikidata_countries=wikidata.get("countries", []),
    )

    contract = build_movie_data_contract(
        movie, analytics=_latest_analytics(movie), enrichment=enrichment, omdb_metadata=omdb_metadata,
        opening=analytics["predicted_opening_weekend_usd"], domestic=analytics["predicted_domestic_total_usd"],
    )
    return MovieDetail.model_validate({**detail.model_dump(), **contract})


def _fetch_detail_enrichment(
    movie: Movie,
) -> tuple[dict[str, str | None], dict[str, str | list[str] | None], dict[str, str | list[str] | None]]:
    cache_key = f"movie-detail-enrichment:{movie.id}:{movie.release_date.isoformat()}:{movie.updated_at.isoformat() if movie.updated_at else 'none'}"

    cached = _DETAIL_ENRICHMENT_CACHE.get_or_set(cache_key, lambda: _fetch_detail_enrichment_uncached(movie))
    return cached["omdb"], cached["wikipedia"], cached["wikidata"]


def _fetch_detail_enrichment_uncached(movie: Movie) -> dict[str, dict]:
    tasks = {
        "omdb": lambda: fetch_movie_metadata(movie) or {},
        "wikipedia": lambda: fetch_movie_wikipedia(movie) or {},
        "wikidata": lambda: fetch_movie_wikidata(movie) or {},
    }
    results: dict[str, dict] = {"omdb": {}, "wikipedia": {}, "wikidata": {}}

    # Detail pages call three external metadata providers; fetch them concurrently
    # so one slow provider does not serially block the rest.
    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        future_map = {pool.submit(task): name for name, task in tasks.items()}
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                results[name] = future.result()
            except Exception:
                logger.exception("Detail enrichment failed for provider=%s movie_id=%s", name, movie.id)

    return results


def _parallel_serialize(movies: list[Movie], serializer, max_workers: int = 8) -> list[MovieSummary]:
    """Serialize a list of movies in parallel using a thread pool."""
    if not movies:
        return []

    results: dict[int, MovieSummary] = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(movies))) as pool:
        future_to_movie = {pool.submit(serializer, movie): movie for movie in movies}
        for future in as_completed(future_to_movie):
            movie = future_to_movie[future]
            try:
                results[movie.id] = future.result()
            except Exception:
                logger.exception("Failed to serialize movie id=%s title=%r", movie.id, movie.title)

    # Preserve original ordering
    return [results[m.id] for m in movies if m.id in results]


def _cache_response(data, max_age: int = 60) -> JSONResponse:
    """Wrap data in a JSONResponse with Cache-Control headers."""
    import json
    from fastapi.encoders import jsonable_encoder
    return JSONResponse(
        content=jsonable_encoder(data),
        headers={"Cache-Control": f"public, max-age={max_age}, stale-while-revalidate=30"},
    )


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@router.get("/trending")
def get_trending_movies(
    limit: int = Query(default=6, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Return the top trending movies ordered by buzz score."""
    movies = movie_repository.list_trending_movies(db, limit=limit)
    items = _parallel_serialize(movies, _serialize_summary_fast)
    return _cache_response(items, max_age=120)


@router.get("/upcoming")
def get_upcoming_movies(
    limit: int = Query(default=6, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Return upcoming movies ordered by release date."""
    movies = movie_repository.list_upcoming_movies(db, today=date.today(), limit=limit)
    items = _parallel_serialize(movies, _serialize_summary_fast)
    return _cache_response(items, max_age=300)


@router.get("/released")
def get_released_movies(
    limit: int = Query(default=12, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return released movies ordered by release date descending."""
    movies = movie_repository.list_released_movies(db, today=date.today(), limit=limit)
    items = _parallel_serialize(movies, _serialize_summary_fast)
    return _cache_response(items, max_age=300)


@router.get("/home")
def get_homepage_payload(db: Session = Depends(get_db)):
    trending = _parallel_serialize(movie_repository.list_trending_movies(db, limit=6), _serialize_summary_fast)
    upcoming = _parallel_serialize(movie_repository.list_upcoming_movies(db, today=date.today(), limit=6), _serialize_summary_fast)
    released = _parallel_serialize(movie_repository.list_released_movies(db, today=date.today(), limit=4), _serialize_summary_fast)

    dashboard_movies = movie_repository.list_summary_movies(db)
    tracked = []
    scored_movies: list[tuple[Movie, float]] = []
    for movie in dashboard_movies:
        analytics = _latest_analytics(movie)
        if analytics is None:
            continue
        scored_movies.append((movie, analytics.hype_score))
        tracked.append(
            {
                "buzz_score": analytics.buzz_score,
                "hype_score": analytics.hype_score,
            }
        )

    most_hyped_movies = [movie for movie, _score in sorted(scored_movies, key=lambda item: item[1], reverse=True)[:5]]
    most_hyped = _parallel_serialize(most_hyped_movies, _serialize_summary_fast)
    tracked_movies = len(tracked)

    return _cache_response(
        {
            "trending": trending,
            "upcoming": upcoming,
            "released": released,
            "dashboard": {
                "trending": trending[:5],
                "most_hyped": most_hyped,
                "stats": {
                    "tracked_movies": tracked_movies,
                    "average_hype_score": round(sum(movie["hype_score"] for movie in tracked) / tracked_movies, 2) if tracked_movies else 0.0,
                    "average_buzz_score": round(sum(movie["buzz_score"] for movie in tracked) / tracked_movies, 2) if tracked_movies else 0.0,
                },
            },
        },
        max_age=120,
    )


@router.get("", response_model=list[MovieSummary])
def get_catalog(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return the full movie catalog."""
    movies = movie_repository.list_summary_movies(db, limit=limit)
    return _parallel_serialize(movies, _serialize_summary_fast)


@router.get("/browse", response_model=PaginatedMovieSummaries)
def browse_movie_catalog(
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    genre: str | None = Query(default=None),
    studio: str | None = Query(default=None),
    director: str | None = Query(default=None),
    franchise: str | None = Query(default=None),
    streaming: str | None = Query(default=None),
    year: int | None = Query(default=None),
    min_rating: float | None = Query(default=None, ge=0, le=10),
    min_hype: float | None = Query(default=None, ge=0, le=100),
    min_popularity: float | None = Query(default=None, ge=0),
    sort: str = Query(default="hype"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=48),
    db: Session = Depends(get_db),
):
    """Paginated, filterable movie catalog browser."""
    result = browse_catalog(
        db,
        CatalogBrowseFilters(
            query=q.strip() if q else None,
            status=status if status and status != "all" else None,
            genre=genre if genre and genre != "all" else None,
            studio=studio if studio and studio != "all" else None,
            director=director if director and director != "all" else None,
            franchise=franchise if franchise and franchise != "all" else None,
            streaming=streaming if streaming and streaming != "all" else None,
            year=year,
            min_rating=min_rating,
            min_hype=min_hype,
            min_popularity=min_popularity,
            sort=sort,
            page=page,
            page_size=page_size,
        ),
    )
    items = _parallel_serialize(result.movies, _serialize_summary_fast)
    return PaginatedMovieSummaries(
        items=items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
        facets=CatalogFacets(**result.facets),
    )


@router.get("/slug/{slug}", response_model=MovieDetail)
def get_movie_details_by_slug(slug: str, db: Session = Depends(get_db)):
    """Return full movie detail by URL slug."""
    movie = movie_repository.get_movie_by_slug(db, slug)
    if not movie:
        raise HTTPException(status_code=404, detail=f"Movie '{slug}' not found")
    return _serialize_detail(movie)


@router.post("/sync-tmdb", response_model=RefreshAnalyticsResponse, dependencies=[Depends(_authorize_admin)])
def sync_movies_from_tmdb(db: Session = Depends(get_db)):
    """Trigger a full TMDB catalog sync (admin use)."""
    result = sync_tmdb_catalog(db)
    clear_browse_cache()
    logger.info(
        "Manual TMDB sync triggered: synced=%s created=%s updated=%s failed=%s",
        result.synced_movies, result.created_movies, result.updated_movies, result.failed_movies,
    )
    return RefreshAnalyticsResponse(
        refreshed_movies=result.synced_movies,
        skipped_movies=0,
        failed_movies=result.failed_movies,
        skipped_reasons=[],
        failed_reasons=result.errors or [],
    )


@router.get("/{movie_id}", response_model=MovieDetail)
def get_movie_details(movie_id: int, db: Session = Depends(get_db)):
    """Return full movie detail by numeric ID."""
    movie = movie_repository.get_movie_by_id(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail=f"Movie id={movie_id} not found")
    return _serialize_detail(movie)
