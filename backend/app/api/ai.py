from app.services.provider_metadata import normalize_metadata
"""Read-only analysis of the currently stored observations."""
from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories import movies as movie_repository
from app.schemas.ai import MovieAIOverviewResponse
from app.services.ai_foundation import build_public_opinion, is_sourced_discussion
from app.services.catalog_enrichment import get_enrichment
from app.services.movie_data import build_movie_data_contract
from app.services.review_analysis import analyze_review_landscape

router = APIRouter()


@router.get("/movie/{movie_id}", response_model=MovieAIOverviewResponse)
def get_movie_ai_overview(movie_id: int, db: Session = Depends(get_db)):
    movie = movie_repository.get_movie_by_id(db, movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    analytics = next((a for a in movie.analytics_snapshots if a.snapshot_label == "latest"), None)
    discussions = [d for d in movie.discussions if is_sourced_discussion(d)]
    opinion = build_public_opinion(discussions)
    enrichment = get_enrichment(movie)
    metadata = normalize_metadata(getattr(movie, "provider_metadata", None))
    landscape = analyze_review_landscape(movie, discussions, enrichment, metadata)
    # Missing reviews are missing evidence, not neutral reviews or generated opinions.
    for key in ("critics", "audience"):
        perspective = landscape[key]
        if not perspective.item_count:
            perspective.summary = f"No sourced {key} discussion is stored for this title."
            perspective.top_themes = []
            perspective.positive_drivers = []
            perspective.negative_drivers = []
    timestamp = analytics.last_updated if analytics else movie.updated_at or movie.created_at
    timestamp = timestamp or datetime.now(timezone.utc)
    forecast = build_movie_data_contract(
        movie, analytics=analytics, enrichment=enrichment, omdb_metadata=metadata,
        opening=analytics.predicted_opening_weekend_usd if analytics else 0,
        domestic=analytics.predicted_domestic_total_usd if analytics else 0,
    )
    return {
        "sentiment": {
            "movie_id": movie_id, "snapshot_at": timestamp,
            "positive_count": opinion["positive_count"], "neutral_count": opinion["neutral_count"],
            "negative_count": opinion["negative_count"], "sentiment_score": opinion["average_sentiment"],
            "sample_size": len(discussions), "model_version": "stored-discussion-keywords-v1",
        },
        "prediction": {
            **forecast, "movie_id": movie_id, "snapshot_at": timestamp,
            "feature_version": "attention-heuristic-v1", "model_version": "experimental-heuristic-v1",
            "methodology": "Experimental heuristic; no validated accuracy or calibrated confidence interval."
                if forecast["forecast_status"] == "modeled" else forecast["forecast_note"],
        },
        "summary": {
            "movie_id": movie_id, "snapshot_at": timestamp,
            "audience_summary": landscape["audience"].summary,
            "critic_summary": landscape["critics"].summary,
            "key_themes": opinion["top_themes"], "model_version": "stored-discussion-keywords-v1",
        },
        "public_opinion": opinion,
        "critic_vs_audience": {**landscape, "critics": asdict(landscape["critics"]), "audience": asdict(landscape["audience"])},
        "discussions": [
            {key: getattr(d, key) for key in ("source", "title", "body", "author", "engagement_score", "created_at", "url")}
            for d in sorted(discussions, key=lambda d: d.engagement_score, reverse=True)[:5]
        ],
    }
