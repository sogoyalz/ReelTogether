from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.schemas.analytics import RefreshAnalyticsResponse
from app.schemas.movie import CatalogFacets, MovieDetail, MovieSummary, PaginatedMovieSummaries
from app.db.session import get_db
from app.models.movie import Movie
from app.repositories import movies as movie_repository
from app.services.catalog_browser import CatalogBrowseFilters, browse_catalog, clear_browse_cache
from app.services.catalog_enrichment import get_enrichment
from app.services.omdb import fetch_movie_metadata
from app.services.tmdb import sync_tmdb_catalog
from app.services.wikidata import fetch_movie_wikidata
from app.services.wikipedia import fetch_movie_wikipedia

router = APIRouter()


def _latest_analytics(movie: Movie):
    return next(
        (snapshot for snapshot in movie.analytics_snapshots if snapshot.snapshot_label == "latest"),
        None,
    )


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


def _serialize_summary(movie: Movie) -> MovieSummary:
    analytics = _analytics_payload(movie)
    enrichment = get_enrichment(movie)
    omdb_metadata = fetch_movie_metadata(movie) or {}

    return MovieSummary(
        id=movie.id,
        tmdb_id=movie.tmdb_id,
        slug=movie.slug,
        title=movie.title,
        release_date=movie.release_date,
        status=movie.status,
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
    omdb_metadata = fetch_movie_metadata(movie) or {}
    enrichment = get_enrichment(movie)
    wikipedia = fetch_movie_wikipedia(movie) or {}
    wikidata = fetch_movie_wikidata(movie) or {}

    return MovieDetail(
        **_serialize_summary(movie).model_dump(),
        trailer_url=analytics["trailer_url"],
        trailer_views=analytics["youtube_views"],
        social_mentions=analytics["x_mentions"] + analytics["reddit_mentions"],
        google_trends_score=analytics["google_trends_score"],
        sentiment_score=analytics["sentiment_score"],
        predicted_opening_weekend_usd=analytics["predicted_opening_weekend_usd"],
        predicted_domestic_total_usd=analytics["predicted_domestic_total_usd"],
        imdb_id=omdb_metadata.get("imdb_id"),
        rated=omdb_metadata.get("rated"),
        runtime=omdb_metadata.get("runtime"),
        box_office=omdb_metadata.get("box_office"),
        awards=omdb_metadata.get("awards"),
        metascore=omdb_metadata.get("metascore"),
        imdb_rating=omdb_metadata.get("imdb_rating"),
        imdb_votes=omdb_metadata.get("imdb_votes"),
        rotten_tomatoes=omdb_metadata.get("rotten_tomatoes"),
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


@router.get("/trending", response_model=list[MovieSummary])
async def get_trending_movies(
    limit: int = Query(default=6, ge=1, le=20),
    db: Session = Depends(get_db),
):
    movies = movie_repository.list_trending_movies(db, limit=limit)
    return [_serialize_summary(movie) for movie in movies]


@router.get("/upcoming", response_model=list[MovieSummary])
async def get_upcoming_movies(
    limit: int = Query(default=6, ge=1, le=20),
    db: Session = Depends(get_db),
):
    movies = movie_repository.list_upcoming_movies(db, today=date.today(), limit=limit)
    return [_serialize_summary(movie) for movie in movies]


@router.get("/released", response_model=list[MovieSummary])
async def get_released_movies(
    limit: int = Query(default=12, ge=1, le=100),
    db: Session = Depends(get_db),
):
    movies = movie_repository.list_released_movies(db, today=date.today(), limit=limit)
    return [_serialize_summary(movie) for movie in movies]


@router.get("", response_model=list[MovieSummary])
async def get_catalog(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    movies = movie_repository.list_movies(db)[:limit]
    return [_serialize_summary(movie) for movie in movies]


@router.get("/browse", response_model=PaginatedMovieSummaries)
async def browse_movie_catalog(
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    genre: str | None = Query(default=None),
    studio: str | None = Query(default=None),
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
    result = browse_catalog(
        db,
        CatalogBrowseFilters(
            query=q.strip() if q else None,
            status=status if status and status != "all" else None,
            genre=genre if genre and genre != "all" else None,
            studio=studio if studio and studio != "all" else None,
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
    return PaginatedMovieSummaries(
        items=[_serialize_summary(movie) for movie in result.movies],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
        facets=CatalogFacets(**result.facets),
    )


@router.get("/slug/{slug}", response_model=MovieDetail)
async def get_movie_details_by_slug(slug: str, db: Session = Depends(get_db)):
    movie = movie_repository.get_movie_by_slug(db, slug)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return _serialize_detail(movie)


@router.post("/sync-tmdb", response_model=RefreshAnalyticsResponse)
async def sync_movies_from_tmdb(db: Session = Depends(get_db)):
    result = sync_tmdb_catalog(db)
    clear_browse_cache()
    return RefreshAnalyticsResponse(
        refreshed_movies=result.synced_movies,
        skipped_movies=0,
        failed_movies=result.failed_movies,
        skipped_reasons=[],
        failed_reasons=result.errors or [],
    )


@router.get("/{movie_id}", response_model=MovieDetail)
async def get_movie_details(movie_id: int, db: Session = Depends(get_db)):
    movie = movie_repository.get_movie_by_id(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return _serialize_detail(movie)
