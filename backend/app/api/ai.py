from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories import movies as movie_repository
from app.schemas.ai import (
    CriticAudienceComparisonResponse,
    DiscussionItem,
    MovieAIOverviewResponse,
    MoviePredictionSnapshotResponse,
    PredictionFeatureImportanceResponse,
    PublicOpinionResponse,
    PublicOpinionSourceBreakdown,
    ReviewPerspectiveResponse,
    MovieSentimentSnapshotResponse,
    MovieSummarySnapshotResponse,
    ThemeSignalResponse,
)
from app.services.ai_foundation import ensure_ai_foundation_for_movie, get_ai_overview

router = APIRouter()


@router.get("/movie/{movie_id}", response_model=MovieAIOverviewResponse)
async def get_movie_ai_overview(movie_id: int, db: Session = Depends(get_db)):
    movie = movie_repository.get_movie_by_id(db, movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    overview = get_ai_overview(db, movie_id)
    if overview is None:
        if ensure_ai_foundation_for_movie(db, movie):
            db.commit()
            overview = get_ai_overview(db, movie_id)
    if overview is None:
        raise HTTPException(status_code=404, detail="AI overview not found")

    summary = overview["summary"]
    return MovieAIOverviewResponse(
        sentiment=MovieSentimentSnapshotResponse(
            movie_id=movie_id,
            snapshot_at=overview["sentiment"].snapshot_at,
            positive_count=overview["sentiment"].positive_count,
            neutral_count=overview["sentiment"].neutral_count,
            negative_count=overview["sentiment"].negative_count,
            sentiment_score=overview["sentiment"].sentiment_score,
            sample_size=overview["sentiment"].sample_size,
            model_version=overview["sentiment"].model_version,
        ),
        prediction=MoviePredictionSnapshotResponse(
            movie_id=movie_id,
            snapshot_at=overview["prediction"].snapshot_at,
            predicted_opening_weekend_usd=overview["prediction"].predicted_opening_weekend_usd,
            predicted_domestic_total_usd=overview["prediction"].predicted_domestic_total_usd,
            confidence_score=overview["prediction"].confidence_score,
            opening_weekend_low_usd=overview["prediction_payload"]["opening_weekend_low_usd"],
            opening_weekend_high_usd=overview["prediction_payload"]["opening_weekend_high_usd"],
            domestic_total_low_usd=overview["prediction_payload"]["domestic_total_low_usd"],
            domestic_total_high_usd=overview["prediction_payload"]["domestic_total_high_usd"],
            methodology=overview["prediction_payload"]["methodology"],
            feature_version=overview["prediction"].feature_version,
            model_version=overview["prediction"].model_version,
            feature_importance=[
                PredictionFeatureImportanceResponse(**item)
                for item in overview["prediction_payload"]["feature_importance"]
            ],
        ),
        summary=MovieSummarySnapshotResponse(
            movie_id=movie_id,
            snapshot_at=summary.snapshot_at,
            audience_summary=summary.audience_summary,
            critic_summary=summary.critic_summary,
            key_themes=[theme.strip() for theme in summary.key_themes.split(",") if theme.strip()],
            model_version=summary.model_version,
        ),
        public_opinion=PublicOpinionResponse(
            overall_summary=overview["public_opinion"]["overall_summary"],
            positive_count=overview["public_opinion"]["positive_count"],
            neutral_count=overview["public_opinion"]["neutral_count"],
            negative_count=overview["public_opinion"]["negative_count"],
            average_sentiment=overview["public_opinion"]["average_sentiment"],
            top_themes=overview["public_opinion"]["top_themes"],
            source_breakdown=[
                PublicOpinionSourceBreakdown(**item)
                for item in overview["public_opinion"]["source_breakdown"]
            ],
            highlighted_quotes=overview["public_opinion"]["highlighted_quotes"],
        ),
        critic_vs_audience=CriticAudienceComparisonResponse(
            critics=ReviewPerspectiveResponse(
                label=overview["critic_vs_audience"]["critics"].label,
                item_count=overview["critic_vs_audience"]["critics"].item_count,
                sentiment_score=overview["critic_vs_audience"]["critics"].sentiment_score,
                summary=overview["critic_vs_audience"]["critics"].summary,
                top_themes=overview["critic_vs_audience"]["critics"].top_themes,
                positive_drivers=overview["critic_vs_audience"]["critics"].positive_drivers,
                negative_drivers=overview["critic_vs_audience"]["critics"].negative_drivers,
                highlighted_quotes=overview["critic_vs_audience"]["critics"].highlighted_quotes,
            ),
            audience=ReviewPerspectiveResponse(
                label=overview["critic_vs_audience"]["audience"].label,
                item_count=overview["critic_vs_audience"]["audience"].item_count,
                sentiment_score=overview["critic_vs_audience"]["audience"].sentiment_score,
                summary=overview["critic_vs_audience"]["audience"].summary,
                top_themes=overview["critic_vs_audience"]["audience"].top_themes,
                positive_drivers=overview["critic_vs_audience"]["audience"].positive_drivers,
                negative_drivers=overview["critic_vs_audience"]["audience"].negative_drivers,
                highlighted_quotes=overview["critic_vs_audience"]["audience"].highlighted_quotes,
            ),
            consensus_themes=overview["critic_vs_audience"]["consensus_themes"],
            divergence_themes=overview["critic_vs_audience"]["divergence_themes"],
            alignment_score=overview["critic_vs_audience"]["alignment_score"],
            theme_signals=[
                ThemeSignalResponse(**item)
                for item in overview["critic_vs_audience"]["theme_signals"]
            ],
        ),
        discussions=[
            DiscussionItem(
                source=item.source,
                title=item.title,
                body=item.body,
                author=item.author,
                engagement_score=item.engagement_score,
                created_at=item.created_at,
                url=item.url,
            )
            for item in overview["discussions"]
        ],
    )
