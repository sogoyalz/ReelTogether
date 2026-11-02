"""Public movie endpoints backed by persisted data and bounded catalog queries."""
from __future__ import annotations

from app.schemas.identifiers import MovieId

from datetime import date, datetime, timezone

from app.api.admin import _authorize_admin
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.schemas.discovery import HomePagePayload
from app.schemas.movie import CatalogFacets, MovieDetail, MovieSummary, PaginatedMovieSummaries
from app.db.session import get_db
from app.models.movie import Movie
from app.repositories import movies as movie_repository
from app.services.catalog_browser import CatalogBrowseFilters, browse_catalog, clear_browse_cache
from app.services.catalog_enrichment import get_enrichment
from app.services.movie_data import build_movie_data_contract
from app.services.provider_metadata import normalize_metadata
from app.services.movie_serialization import latest_analytics as _latest_analytics, analytics_payload as _analytics_payload, serialize_summary as _serialize_summary_fast


router = APIRouter()

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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
    # Core detail reads are bounded by the database, never external providers.
    # Catalog maintenance persists provider metadata before it is served here.
    return normalize_metadata(movie.provider_metadata), {}, {}


def _serialize_many(movies: list[Movie], serializer) -> list[MovieSummary]:
    # Serialization is offline; ORM access stays on its owning request thread.
    return [serializer(movie) for movie in movies]


def _cache_response(data, max_age: int = 60, schema=None) -> JSONResponse:
    """Wrap data in a JSONResponse with Cache-Control headers."""
    from fastapi.encoders import jsonable_encoder
    if schema is not None:
        data = schema.model_validate(data)
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
    items = _serialize_many(movies, _serialize_summary_fast)
    return _cache_response(items, max_age=120)


@router.get("/upcoming")
def get_upcoming_movies(
    limit: int = Query(default=6, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Return upcoming movies ordered by release date."""
    movies = movie_repository.list_upcoming_movies(db, today=date.today(), limit=limit)
    items = _serialize_many(movies, _serialize_summary_fast)
    return _cache_response(items, max_age=300)


@router.get("/released")
def get_released_movies(
    limit: int = Query(default=12, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return released movies ordered by release date descending."""
    movies = movie_repository.list_released_movies(db, today=date.today(), limit=limit)
    items = _serialize_many(movies, _serialize_summary_fast)
    return _cache_response(items, max_age=300)


@router.get("/home", response_model=HomePagePayload)
def get_homepage_payload(db: Session = Depends(get_db)):
    trending = _serialize_many(movie_repository.list_trending_movies(db, limit=6), _serialize_summary_fast)
    upcoming = _serialize_many(movie_repository.list_upcoming_movies(db, today=date.today(), limit=6), _serialize_summary_fast)
    released = _serialize_many(movie_repository.list_released_movies(db, today=date.today(), limit=4), _serialize_summary_fast)

    stats = movie_repository.catalog_dashboard_stats(db)
    most_hyped = _serialize_many(movie_repository.list_most_hyped_movies(db), _serialize_summary_fast)

    return _cache_response(
        {
            "trending": trending,
            "upcoming": upcoming,
            "released": released,
            "dashboard": {
                "updated_at": datetime.now(timezone.utc),
                "trending": trending[:5],
                "most_hyped": most_hyped,
                "stats": stats,
            },
        },
        max_age=120, schema=HomePagePayload,
    )


@router.get("", response_model=list[MovieSummary])
def get_catalog(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return the full movie catalog."""
    movies = movie_repository.list_summary_movies(db, limit=limit)
    return _serialize_many(movies, _serialize_summary_fast)


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
    items = _serialize_many(result.movies, _serialize_summary_fast)
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
    movie = movie_repository.get_movie_by_slug(db, slug, with_history=False)
    if not movie:
        raise HTTPException(status_code=404, detail=f"Movie '{slug}' not found")
    return _serialize_detail(movie)


@router.post("/sync-tmdb", status_code=202, dependencies=[Depends(_authorize_admin)], deprecated=True)
def sync_movies_from_tmdb():
    """Compatibility URL: enqueue the same durable job as /admin/jobs/tmdb-sync."""
    from app.api.admin import enqueue_response
    from app.services.startup_jobs import enqueue_tmdb_sync
    return enqueue_response(enqueue_tmdb_sync)


@router.get("/{movie_id}", response_model=MovieDetail)
def get_movie_details(movie_id: MovieId, db: Session = Depends(get_db)):
    """Return full movie detail by numeric ID."""
    movie = movie_repository.get_movie_by_id(db, movie_id, with_history=False)
    if not movie:
        raise HTTPException(status_code=404, detail=f"Movie id={movie_id} not found")
    return _serialize_detail(movie)
