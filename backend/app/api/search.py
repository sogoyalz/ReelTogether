from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.schemas.discovery import (
    AutocompleteSuggestion,
    DashboardBucket,
    DiscoveryDashboardResponse,
    DiscoveryMovieSummary,
)
from app.schemas.movie import CatalogFacets, MovieSummary, PaginatedMovieSummaries
from app.db.session import get_db
from app.models.movie import Movie
from app.repositories import movies as movie_repository
from app.services.catalog_browser import CatalogBrowseFilters, browse_catalog
from app.services.catalog_enrichment import get_enrichment
from app.services.omdb import fetch_movie_metadata
from app.services.tmdb import sync_tmdb_search_results

router = APIRouter()


def _latest_analytics(movie: Movie):
    return next(
        (snapshot for snapshot in movie.analytics_snapshots if snapshot.snapshot_label == "latest"),
        None,
    )


def _ensure_search_inventory(db: Session, query: str, minimum_matches: int, import_limit: int) -> list[Movie]:
    matches = movie_repository.search_movies(db, query)
    if len(query) < 3 or len(matches) >= minimum_matches:
        return matches

    sync_tmdb_search_results(db, query, limit=import_limit)
    return movie_repository.search_movies(db, query)


@router.get("", response_model=PaginatedMovieSummaries)
async def search_movies(
    q: str = Query(..., min_length=1),
    status: str | None = Query(default=None),
    genre: str | None = Query(default=None),
    franchise: str | None = Query(default=None),
    studio: str | None = Query(default=None),
    year: int | None = Query(default=None),
    min_rating: float | None = Query(default=None, ge=0, le=10),
    min_hype: float | None = Query(default=None, ge=0, le=100),
    min_popularity: float | None = Query(default=None, ge=0),
    sort: str = Query(default="hype"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=48),
    db: Session = Depends(get_db),
):
    query = q.strip().lower()
    _ensure_search_inventory(db, query, minimum_matches=6, import_limit=4)
    result = browse_catalog(
        db,
        CatalogBrowseFilters(
            query=query,
            status=status if status and status != "all" else None,
            genre=genre if genre and genre != "all" else None,
            franchise=franchise if franchise and franchise != "all" else None,
            studio=studio if studio and studio != "all" else None,
            year=year,
            min_rating=min_rating,
            min_hype=min_hype,
            min_popularity=min_popularity,
            sort=sort,
            page=page,
            page_size=page_size,
        ),
    )
    response = []
    for movie in result.movies:
        analytics = _latest_analytics(movie)
        if analytics is None:
            continue
        enrichment = get_enrichment(movie)
        omdb_metadata = fetch_movie_metadata(movie) or {}
        response.append(
            MovieSummary(
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
                buzz_score=analytics.buzz_score,
                hype_score=analytics.hype_score,
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
        )
    return PaginatedMovieSummaries(
        items=response,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
        facets=CatalogFacets(**result.facets),
    )


@router.get("/suggest", response_model=list[AutocompleteSuggestion])
async def suggest_movies(q: str = Query(..., min_length=1), limit: int = Query(default=6, ge=1, le=10), db: Session = Depends(get_db)):
    query = q.strip().lower()
    matches = movie_repository.search_movies(db, query)
    if len(query) >= 4 and len(matches) < max(2, limit // 2):
        matches = _ensure_search_inventory(db, query, minimum_matches=max(2, limit // 2), import_limit=min(limit, 3))
    matches = matches[:limit]
    return [
        AutocompleteSuggestion(
            id=movie.id,
            slug=movie.slug,
            title=movie.title,
            status=movie.status,
            release_date=movie.release_date,
        )
        for movie in matches
    ]


@router.get("/dashboard", response_model=DiscoveryDashboardResponse)
async def discovery_dashboard(db: Session = Depends(get_db)):
    movies = movie_repository.list_movies(db)
    summaries: list[DiscoveryMovieSummary] = []
    genre_buckets: dict[str, list[float]] = defaultdict(list)
    franchise_buckets: dict[str, list[float]] = defaultdict(list)

    for movie in movies:
        analytics = _latest_analytics(movie)
        if analytics is None:
            continue

        enrichment = get_enrichment(movie)
        summary = DiscoveryMovieSummary(
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
            buzz_score=analytics.buzz_score,
            hype_score=analytics.hype_score,
            franchise=enrichment["franchise"],
            studios=enrichment["studios"],
            streaming_on=enrichment["streaming_on"],
            cast=enrichment["cast"],
            directors=enrichment["directors"],
        )
        summaries.append(summary)
        for genre in movie.genres:
            genre_buckets[genre].append(analytics.hype_score)
        if enrichment["franchise"]:
            franchise_buckets[enrichment["franchise"]].append(analytics.hype_score)

    trending_by_genre = _serialize_buckets(genre_buckets)
    trending_by_franchise = _serialize_buckets(franchise_buckets)
    editorial_collections = {
        "most_hyped_upcoming_sci_fi": [
            movie for movie in sorted(
                [summary for summary in summaries if summary.status != "released" and "Sci-Fi" in summary.genres],
                key=lambda item: item.hype_score,
                reverse=True,
            )[:4]
        ],
        "biggest_trailer_reach": [
            movie for movie in sorted(summaries, key=lambda item: item.buzz_score, reverse=True)[:4]
        ],
    }
    return DiscoveryDashboardResponse(
        trending_by_genre=trending_by_genre,
        trending_by_franchise=trending_by_franchise,
        editorial_collections=editorial_collections,
    )


def _serialize_buckets(buckets: dict[str, list[float]]) -> list[DashboardBucket]:
    return [
        DashboardBucket(
            label=label,
            movie_count=len(scores),
            average_hype_score=round(sum(scores) / len(scores), 2),
        )
        for label, scores in sorted(
            buckets.items(),
            key=lambda item: (sum(item[1]) / len(item[1]), len(item[1])),
            reverse=True,
        )[:6]
    ]
