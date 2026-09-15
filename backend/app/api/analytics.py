from app.api.admin import _authorize_admin
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.schemas.analytics import (
    AnalyticsHistoryPoint,
    AnalyticsHistoryResponse,
    CompareMoviesResponse,
    ComparisonEntry,
    MovieAnalyticsResponse,
    RefreshAnalyticsResponse,
    ScoreBreakdown,
    SentimentTimelinePoint,
    SentimentTimelineResponse,
    SentimentBreakdown,
)
from app.db.session import get_db
from app.repositories import movies as movie_repository
from app.services.catalog_enrichment import build_history, build_score_breakdown
from app.services.catalog_enrichment import get_enrichment
from app.services.movie_data import build_movie_data_contract
from app.services.omdb import fetch_movie_metadata
from app.services.review_fetcher import build_sentiment_timeline, refresh_review_sentiments_for_movie
from app.services.youtube_analytics import refresh_all_movie_analytics, refresh_movie_analytics

router = APIRouter()


@router.get("/dashboard")
def get_dashboard_snapshot(db: Session = Depends(get_db)):
    movies = movie_repository.list_movies(db)
    serialized = []
    for movie in movies:
        analytics = next(
            (snapshot for snapshot in movie.analytics_snapshots if snapshot.snapshot_label == "latest"),
            None,
        )
        if analytics is None:
            continue
        serialized.append(
            {
                "id": movie.id,
                "tmdb_id": movie.tmdb_id,
                "slug": movie.slug,
                "title": movie.title,
                "release_date": movie.release_date,
                "status": movie.status,
                "poster_url": movie.poster_url,
                "backdrop_url": movie.backdrop_url,
                "overview": movie.overview,
                "genres": movie.genres,
                "tmdb_popularity": movie.tmdb_popularity,
                "buzz_score": analytics.buzz_score,
                "hype_score": analytics.hype_score,
            }
        )
    trending = sorted(serialized, key=lambda movie: movie["buzz_score"], reverse=True)[:5]
    most_hyped = sorted(serialized, key=lambda movie: movie["hype_score"], reverse=True)[:5]
    tracked_movies = len(serialized)
    return {
        "updated_at": datetime.utcnow(),
        "trending": trending,
        "most_hyped": most_hyped,
        "stats": {
            "tracked_movies": tracked_movies,
            "average_hype_score": round(sum(movie["hype_score"] for movie in serialized) / tracked_movies, 2) if tracked_movies else 0.0,
            "average_buzz_score": round(sum(movie["buzz_score"] for movie in serialized) / tracked_movies, 2) if tracked_movies else 0.0,
        },
    }


@router.get("/movie/{movie_id}", response_model=MovieAnalyticsResponse)
def get_movie_analytics(movie_id: int, db: Session = Depends(get_db)):
    movie = movie_repository.get_movie_by_id(db, movie_id)
    analytics = movie_repository.get_movie_analytics(db, movie_id)
    if not movie or not analytics:
        raise HTTPException(status_code=404, detail="Movie not found")
    enrichment = get_enrichment(movie)
    omdb_metadata = fetch_movie_metadata(movie) or {}
    canonical = build_movie_data_contract(
        movie,
        analytics=analytics,
        enrichment=enrichment,
        omdb_metadata=omdb_metadata,
        opening=analytics.predicted_opening_weekend_usd,
        domestic=analytics.predicted_domestic_total_usd,
    )

    return MovieAnalyticsResponse(
        movie_id=movie.id,
        movie_title=movie.title,
        snapshot_date=analytics.snapshot_date,
        youtube_views=analytics.youtube_views,
        youtube_likes=analytics.youtube_likes,
        youtube_comments=analytics.youtube_comments,
        google_trends_score=analytics.google_trends_score,
        x_mentions=analytics.x_mentions,
        reddit_mentions=analytics.reddit_mentions,
        social_mentions=analytics.x_mentions + analytics.reddit_mentions,
        sentiment_score=analytics.sentiment_score,
        sentiment_breakdown=SentimentBreakdown(
            positive=analytics.sentiment_positive,
            neutral=analytics.sentiment_neutral,
            negative=analytics.sentiment_negative,
        ),
        buzz_score=analytics.buzz_score,
        hype_score=analytics.hype_score,
        predicted_opening_weekend_usd=canonical["predicted_opening_weekend_usd"],
        predicted_domestic_total_usd=canonical["predicted_domestic_total_usd"],
        forecast_is_public=canonical["forecast_is_public"],
        forecast_status=canonical["forecast_status"],
        forecast_note=canonical["forecast_note"],
        engagement_metrics_are_estimated=canonical["engagement_metrics_are_estimated"],
        engagement_metrics_note=canonical["engagement_metrics_note"],
        data_quality=canonical["data_quality"],
        field_sources=canonical["field_sources"],
        last_verified_at=canonical["last_verified_at"],
        warnings=canonical["warnings"],
        trailer_url=analytics.trailer_url,
        updated_at=analytics.last_updated,
        score_breakdown=ScoreBreakdown(**build_score_breakdown(movie, analytics)),
    )


@router.get("/movie/{movie_id}/history", response_model=AnalyticsHistoryResponse)
def get_movie_analytics_history(movie_id: int, db: Session = Depends(get_db)):
    movie = movie_repository.get_movie_by_id(db, movie_id)
    analytics = movie_repository.get_movie_analytics(db, movie_id)
    if not movie or not analytics:
        raise HTTPException(status_code=404, detail="Movie not found")

    points = [AnalyticsHistoryPoint(**point) for point in build_history(movie, analytics)]
    return AnalyticsHistoryResponse(movie_id=movie.id, movie_title=movie.title, points=points)


@router.get("/compare", response_model=CompareMoviesResponse)
def compare_movies(
    movie_ids: str = Query(..., description="Comma separated movie ids"),
    db: Session = Depends(get_db),
):
    try:
        ids = [int(raw_id) for raw_id in movie_ids.split(",") if raw_id.strip()]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="movie_ids must be a comma separated list of integers") from exc
    if len(ids) != len(set(ids)) or not 2 <= len(ids) <= 4:
        raise HTTPException(status_code=422, detail="Provide between two and four distinct movie ids")
    items = []
    for movie_id in ids:
        movie = movie_repository.get_movie_by_id(db, movie_id)
        analytics = movie_repository.get_movie_analytics(db, movie_id)
        if not movie or not analytics:
            raise HTTPException(status_code=404, detail=f"Movie {movie_id} not found")
        enrichment = get_enrichment(movie)
        omdb_metadata = fetch_movie_metadata(movie) or {}
        canonical = build_movie_data_contract(
            movie,
            analytics=analytics,
            enrichment=enrichment,
            omdb_metadata=omdb_metadata,
            opening=analytics.predicted_opening_weekend_usd,
            domestic=analytics.predicted_domestic_total_usd,
            confidence=0.0,
        )
        items.append(
            ComparisonEntry(
                movie_id=movie.id,
                slug=movie.slug,
                title=movie.title,
                release_date=movie.release_date,
                status=canonical["status"],
                buzz_score=analytics.buzz_score,
                hype_score=analytics.hype_score,
                youtube_views=analytics.youtube_views,
                social_mentions=analytics.x_mentions + analytics.reddit_mentions,
                google_trends_score=analytics.google_trends_score,
                sentiment_score=analytics.sentiment_score,
                predicted_opening_weekend_usd=canonical["predicted_opening_weekend_usd"],
                predicted_domestic_total_usd=canonical["predicted_domestic_total_usd"],
                forecast_is_public=canonical["forecast_is_public"],
                forecast_status=canonical["forecast_status"],
                forecast_note=canonical["forecast_note"],
                engagement_metrics_are_estimated=canonical["engagement_metrics_are_estimated"],
                engagement_metrics_note=canonical["engagement_metrics_note"],
                data_quality=canonical["data_quality"],
                field_sources=canonical["field_sources"],
                last_verified_at=canonical["last_verified_at"],
                warnings=canonical["warnings"],
                tmdb_popularity=movie.tmdb_popularity,
                imdb_rating=omdb_metadata.get("imdb_rating"),
                rotten_tomatoes=omdb_metadata.get("rotten_tomatoes"),
                runtime=omdb_metadata.get("runtime"),
                box_office=omdb_metadata.get("box_office"),
                franchise=enrichment.get("franchise"),
                streaming_on=enrichment.get("streaming_on", []),
                audience_sentiment=None,
                prediction_confidence=None,
                key_themes=[],
            )
        )

    return CompareMoviesResponse(compared_at=datetime.utcnow(), items=items)


@router.post("/refresh", response_model=RefreshAnalyticsResponse, dependencies=[Depends(_authorize_admin)])
def refresh_all_analytics(db: Session = Depends(get_db)):
    result = refresh_all_movie_analytics(db)
    return RefreshAnalyticsResponse(
        refreshed_movies=result.refreshed_movies,
        skipped_movies=result.skipped_movies,
        failed_movies=result.failed_movies,
        skipped_reasons=result.skipped_reasons or [],
        failed_reasons=result.failed_reasons or [],
    )


@router.post("/movie/{movie_id}/refresh", response_model=RefreshAnalyticsResponse, dependencies=[Depends(_authorize_admin)])
def refresh_movie(movie_id: int, db: Session = Depends(get_db)):
    if movie_repository.get_movie_by_id(db, movie_id) is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    result = refresh_movie_analytics(db, movie_id)
    return RefreshAnalyticsResponse(
        refreshed_movies=result.refreshed_movies,
        skipped_movies=result.skipped_movies,
        failed_movies=result.failed_movies,
        skipped_reasons=result.skipped_reasons or [],
        failed_reasons=result.failed_reasons or [],
    )


@router.post("/movie/{movie_id}/sentiment/refresh", dependencies=[Depends(_authorize_admin)])
def refresh_movie_sentiment(movie_id: int, db: Session = Depends(get_db)):
    if movie_repository.get_movie_by_id(db, movie_id) is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return refresh_review_sentiments_for_movie(db, movie_id)


@router.get("/movie/{movie_id}/sentiment/timeline", response_model=SentimentTimelineResponse)
def get_movie_sentiment_timeline(movie_id: int, db: Session = Depends(get_db)):
    movie = movie_repository.get_movie_by_id(db, movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    stored = movie_repository.list_review_sentiments(db, movie_id)
    timeline_payload = build_sentiment_timeline(
        [
            {
                "author": item.author,
                "content": item.content_snippet,
                "created_at": item.created_at,
                "source": item.source,
                "sentiment_score": item.sentiment_score,
                "sentiment_label": item.sentiment_label,
                "confidence": item.confidence,
            }
            for item in stored
        ]
    )

    return SentimentTimelineResponse(
        timeline=[SentimentTimelinePoint(**point) for point in timeline_payload["timeline"]],
        overall_sentiment=timeline_payload["overall_sentiment"],
        total_reviews=timeline_payload["total_reviews"],
        sentiment_trend=timeline_payload["sentiment_trend"],
        positive_pct=timeline_payload["positive_pct"],
        neutral_pct=timeline_payload["neutral_pct"],
        negative_pct=timeline_payload["negative_pct"],
    )
