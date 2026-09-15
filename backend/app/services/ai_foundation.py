from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai import (
    MovieDiscussion,
    MovieFeatureSnapshot,
    MoviePredictionSnapshot,
    MovieSentimentSnapshot,
    MovieSummarySnapshot,
)
from app.models.movie import Movie
from app.services.catalog_enrichment import get_enrichment
from app.services.omdb import fetch_movie_metadata
from app.services.review_analysis import analyze_review_landscape


def ensure_ai_foundation(db: Session) -> None:
    movies = db.scalars(select(Movie)).all()
    dirty = False

    for movie in movies:
        dirty |= ensure_ai_foundation_for_movie(db, movie)

    if dirty:
        db.commit()


def ensure_ai_foundation_for_movie(db: Session, movie: Movie) -> bool:
    dirty = False
    dirty |= _ensure_discussions(db, movie)
    dirty |= _ensure_sentiment_snapshot(db, movie)
    dirty |= _ensure_feature_snapshot(db, movie)
    dirty |= _ensure_prediction_snapshot(db, movie)
    dirty |= _ensure_summary_snapshot(db, movie)
    return dirty


def get_ai_overview(db: Session, movie_id: int) -> dict | None:
    sentiment = db.scalar(
        select(MovieSentimentSnapshot)
        .where(MovieSentimentSnapshot.movie_id == movie_id)
        .order_by(MovieSentimentSnapshot.snapshot_at.desc())
    )
    prediction = db.scalar(
        select(MoviePredictionSnapshot)
        .where(MoviePredictionSnapshot.movie_id == movie_id)
        .order_by(MoviePredictionSnapshot.snapshot_at.desc())
    )
    summary = db.scalar(
        select(MovieSummarySnapshot)
        .where(MovieSummarySnapshot.movie_id == movie_id)
        .order_by(MovieSummarySnapshot.snapshot_at.desc())
    )
    discussions = list(
        db.scalars(
            select(MovieDiscussion)
            .where(MovieDiscussion.movie_id == movie_id)
            .order_by(MovieDiscussion.engagement_score.desc(), MovieDiscussion.created_at.desc())
            .limit(5)
        ).all()
    )

    discussions = [item for item in discussions if is_sourced_discussion(item)]
    if not sentiment or not prediction or not summary:
        return None

    return {
        "sentiment": sentiment,
        "prediction": prediction,
        "summary": summary,
        "public_opinion": build_public_opinion(discussions),
        "discussions": discussions,
    }


def build_public_opinion(discussions: list[MovieDiscussion]) -> dict:
    discussions = [item for item in discussions if is_sourced_discussion(item)]
    if not discussions:
        return {
            "overall_summary": "Public opinion is still limited for this title. More audience discussion is needed before a stable read emerges.",
            "positive_count": 0,
            "neutral_count": 0,
            "negative_count": 0,
            "average_sentiment": 0.0,
            "top_themes": [],
            "source_breakdown": [],
            "highlighted_quotes": [],
        }

    sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
    source_scores: dict[str, list[float]] = {}
    theme_counter: Counter[str] = Counter()
    highlighted_quotes: list[str] = []

    for discussion in discussions:
        sentiment = _discussion_sentiment(discussion)
        sentiment_counts[sentiment] += 1
        source_scores.setdefault(discussion.source, []).append(_sentiment_value(sentiment))
        theme_counter.update(_extract_themes(discussion.body))
        if discussion.source == "youtube" and len(highlighted_quotes) < 3:
            highlighted_quotes.append(discussion.body[:180].strip())

    sample_size = sum(sentiment_counts.values()) or 1
    average_sentiment = round(
        (
            sentiment_counts["positive"] - sentiment_counts["negative"]
        ) / sample_size,
        2,
    )
    tone = "mixed"
    if sentiment_counts["positive"] > sentiment_counts["negative"] * 1.4:
        tone = "mostly positive"
    elif sentiment_counts["negative"] > sentiment_counts["positive"] * 1.2:
        tone = "skeptical"

    top_themes = [theme for theme, _ in theme_counter.most_common(4)]
    overall_summary = (
        f"Current public opinion is {tone}, with {sentiment_counts['positive']} positive, "
        f"{sentiment_counts['neutral']} neutral, and {sentiment_counts['negative']} negative discussion items. "
        f"The main audience conversation is centering on {', '.join(top_themes) if top_themes else 'general movie buzz'}."
    )

    source_breakdown = [
        {
            "source": source,
            "item_count": len(scores),
            "average_sentiment": round(sum(scores) / len(scores), 2) if scores else 0.0,
        }
        for source, scores in sorted(source_scores.items(), key=lambda item: item[0])
    ]

    return {
        "overall_summary": overall_summary,
        "positive_count": sentiment_counts["positive"],
        "neutral_count": sentiment_counts["neutral"],
        "negative_count": sentiment_counts["negative"],
        "average_sentiment": average_sentiment,
        "top_themes": top_themes,
        "source_breakdown": source_breakdown,
        "highlighted_quotes": highlighted_quotes,
    }


def _ensure_discussions(db: Session, movie: Movie) -> bool:
    # Provider ingestion is the only source of discussions. Never synthesize quotes.
    return False


def is_sourced_discussion(discussion: MovieDiscussion) -> bool:
    try:
        payload = json.loads(discussion.raw_payload or "{}")
    except (TypeError, json.JSONDecodeError):
        payload = {}
    return not payload.get("seeded") and bool(discussion.url) and "example.com" not in discussion.url


def _ensure_sentiment_snapshot(db: Session, movie: Movie) -> bool:
    if _snapshot_is_current(db, MovieSentimentSnapshot, movie):
        return False
    discussions = [d for d in movie.discussions if is_sourced_discussion(d)]
    opinion = build_public_opinion(discussions)
    db.add(MovieSentimentSnapshot(
        movie_id=movie.id, snapshot_at=datetime.utcnow(),
        positive_count=opinion["positive_count"], neutral_count=opinion["neutral_count"],
        negative_count=opinion["negative_count"], sentiment_score=opinion["average_sentiment"],
        sample_size=len(discussions), model_version="stored-discussion-keywords-v1",
    ))
    return True


def _ensure_feature_snapshot(db: Session, movie: Movie) -> bool:
    if _snapshot_is_current(db, MovieFeatureSnapshot, movie):
        return False

    analytics = _latest_analytics(movie)
    omdb = movie.provider_metadata or {}
    views = analytics.youtube_views if analytics else 0
    likes = analytics.youtube_likes if analytics else 0
    comments = analytics.youtube_comments if analytics else 0
    feature = MovieFeatureSnapshot(
        movie_id=movie.id,
        snapshot_at=datetime.utcnow(),
        release_days_until=(movie.release_date - date.today()).days,
        trailer_views=views,
        likes_to_views_ratio=round((likes / views) if views else 0.0, 4),
        comments_to_views_ratio=round((comments / views) if views else 0.0, 4),
        reddit_mentions=analytics.reddit_mentions if analytics else 0,
        social_mentions=(analytics.x_mentions + analytics.reddit_mentions) if analytics else 0,
        tmdb_popularity=movie.tmdb_popularity,
        imdb_rating=_parse_float(omdb.get("imdb_rating")),
        sentiment_score=analytics.sentiment_score if analytics else 0.0,
        feature_version="bootstrap-feature-v1",
    )
    db.add(feature)
    return True


def _ensure_prediction_snapshot(db: Session, movie: Movie) -> bool:
    if _snapshot_is_current(db, MoviePredictionSnapshot, movie):
        return False

    analytics = _latest_analytics(movie)
    omdb = movie.provider_metadata or {}
    rating = _parse_float(omdb.get("imdb_rating"))
    franchise_bonus = 1.12 if get_enrichment(movie).get("franchise") else 1.0
    rating_bonus = 1 + min(rating / 25, 0.28)
    popularity_bonus = 1 + min(movie.tmdb_popularity / 220, 0.35)
    opening = (analytics.predicted_opening_weekend_usd if analytics else 12_000_000.0) * franchise_bonus * rating_bonus
    total = (analytics.predicted_domestic_total_usd if analytics else opening * 2.8) * popularity_bonus
    confidence = 0.0  # No held-out calibration exists.
    snapshot = MoviePredictionSnapshot(
        movie_id=movie.id,
        snapshot_at=datetime.utcnow(),
        predicted_opening_weekend_usd=round(opening, 2),
        predicted_domestic_total_usd=round(total, 2),
        confidence_score=round(confidence, 2),
        feature_version="bootstrap-feature-v1",
        model_version="experimental-heuristic-v1",
    )
    db.add(snapshot)
    return True


def _ensure_summary_snapshot(db: Session, movie: Movie) -> bool:
    if _snapshot_is_current(db, MovieSummarySnapshot, movie):
        return False

    enrichment = get_enrichment(movie)
    omdb = movie.provider_metadata or {}
    discussions = [d for d in movie.discussions if is_sourced_discussion(d)]
    landscape = analyze_review_landscape(movie, discussions, enrichment, omdb)
    audience_summary = landscape["audience"].summary if landscape["audience"].item_count else "No sourced audience discussions are stored."
    critic_summary = landscape["critics"].summary if landscape["critics"].item_count else "No sourced critic discussions are stored."
    themes = build_public_opinion(discussions)["top_themes"]
    snapshot = MovieSummarySnapshot(
        movie_id=movie.id,
        snapshot_at=datetime.utcnow(),
        audience_summary=audience_summary,
        critic_summary=critic_summary,
        key_themes=", ".join(themes[:5]),
        model_version="stored-discussion-keywords-v1",
    )
    db.add(snapshot)
    return True


def _latest_analytics(movie: Movie):
    return next(
        (snapshot for snapshot in movie.analytics_snapshots if snapshot.snapshot_label == "latest"),
        None,
    )


def _parse_float(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def _discussion_sentiment(discussion: MovieDiscussion) -> str:
    payload = {}
    if discussion.raw_payload:
        try:
            payload = json.loads(discussion.raw_payload)
        except json.JSONDecodeError:
            payload = {}
    sentiment = payload.get("sentiment")
    if sentiment in {"positive", "neutral", "negative"}:
        return sentiment

    text = discussion.body.lower()
    positive_hits = sum(word in text for word in ("love", "great", "amazing", "hype", "excellent", "fun"))
    negative_hits = sum(word in text for word in ("bad", "boring", "mess", "awful", "weak", "terrible"))
    if positive_hits > negative_hits:
        return "positive"
    if negative_hits > positive_hits:
        return "negative"
    return "neutral"


def _sentiment_value(sentiment: str) -> float:
    if sentiment == "positive":
        return 1.0
    if sentiment == "negative":
        return -1.0
    return 0.0


def _extract_themes(text: str) -> list[str]:
    normalized = text.lower()
    theme_map = {
        "cast": ("cast", "actor", "performance"),
        "visuals": ("visual", "cinematography", "shot", "effects"),
        "story": ("story", "plot", "writing", "script"),
        "trailer": ("trailer", "teaser"),
        "music": ("music", "score", "soundtrack"),
        "action": ("action", "fight", "sequence"),
    }
    return [theme for theme, keywords in theme_map.items() if any(keyword in normalized for keyword in keywords)]


def _snapshot_is_current(db: Session, model, movie: Movie) -> bool:
    latest = db.scalar(select(model).where(model.movie_id == movie.id).order_by(model.snapshot_at.desc()))
    if latest is None:
        return False
    version = getattr(latest, "model_version", getattr(latest, "feature_version", ""))
    if "bootstrap" in version and model is not MovieFeatureSnapshot:
        return False
    analytics = _latest_analytics(movie)
    dates = [movie.updated_at, movie.created_at, analytics.last_updated if analytics else None]
    dates.extend(d.created_at for d in movie.discussions if is_sourced_discussion(d))
    newest = max((d.replace(tzinfo=None) for d in dates if d), default=datetime.min)
    return latest.snapshot_at.replace(tzinfo=None) >= newest
