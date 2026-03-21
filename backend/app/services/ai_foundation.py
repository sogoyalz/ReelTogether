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
    existing = db.scalar(select(MovieDiscussion.id).where(MovieDiscussion.movie_id == movie.id).limit(1))
    if existing is not None:
        return False

    enrichment = get_enrichment(movie)
    themes = movie.genres[:2] + ([enrichment.get("franchise")] if enrichment.get("franchise") else [])
    templates = [
        ("reddit", f"Early audience reaction to {movie.title}", "Fans are focusing on the scale, cast, and whether the story can match the hype."),
        ("reddit", f"Is {movie.title} going to overperform?", "Discussion is centered on trailer momentum, franchise pull, and release timing."),
        ("youtube", f"{movie.title} trailer comment summary", "Viewers are reacting to the visuals, tone, and standout cast moments from the trailer."),
    ]

    for index, (source, title, body) in enumerate(templates, start=1):
        discussion = MovieDiscussion(
            movie_id=movie.id,
            source=source,
            external_id=f"{source}-{movie.slug}-{index}",
            title=title,
            body=f"{body} Key themes include {', '.join([theme for theme in themes if theme][:3]) or 'franchise potential'}.",
            author=f"{source}_editorial_{index}",
            engagement_score=round(55 + movie.tmdb_popularity * 0.8 - index * 2, 2),
            url=f"https://example.com/{source}/{movie.slug}/{index}",
            created_at=datetime.utcnow() - timedelta(hours=index * 7),
            raw_payload=json.dumps({"movie": movie.slug, "source": source, "seeded": True}),
        )
        db.add(discussion)
    return True


def _ensure_sentiment_snapshot(db: Session, movie: Movie) -> bool:
    existing = db.scalar(select(MovieSentimentSnapshot.id).where(MovieSentimentSnapshot.movie_id == movie.id).limit(1))
    if existing is not None:
        return False

    analytics = _latest_analytics(movie)
    social_mentions = (analytics.x_mentions + analytics.reddit_mentions) if analytics else 0
    sample_size = max(80, social_mentions // 180)
    base_positive = 62 if movie.status == "released" else 66
    if analytics and analytics.sentiment_score:
        base_positive = min(82, max(48, int(analytics.sentiment_score * 100) - 8))
    negative = max(8, min(24, 100 - base_positive - 18))
    neutral = 100 - base_positive - negative
    snapshot = MovieSentimentSnapshot(
        movie_id=movie.id,
        snapshot_at=datetime.utcnow(),
        positive_count=int(sample_size * (base_positive / 100)),
        neutral_count=int(sample_size * (neutral / 100)),
        negative_count=max(1, sample_size - int(sample_size * (base_positive / 100)) - int(sample_size * (neutral / 100))),
        sentiment_score=round(((base_positive - negative) / 100), 2),
        sample_size=sample_size,
        model_version="bootstrap-sentiment-v1",
    )
    db.add(snapshot)
    return True


def _ensure_feature_snapshot(db: Session, movie: Movie) -> bool:
    existing = db.scalar(select(MovieFeatureSnapshot.id).where(MovieFeatureSnapshot.movie_id == movie.id).limit(1))
    if existing is not None:
        return False

    analytics = _latest_analytics(movie)
    omdb = fetch_movie_metadata(movie) or {}
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
    existing = db.scalar(select(MoviePredictionSnapshot.id).where(MoviePredictionSnapshot.movie_id == movie.id).limit(1))
    if existing is not None:
        return False

    analytics = _latest_analytics(movie)
    omdb = fetch_movie_metadata(movie) or {}
    rating = _parse_float(omdb.get("imdb_rating"))
    franchise_bonus = 1.12 if get_enrichment(movie).get("franchise") else 1.0
    rating_bonus = 1 + min(rating / 25, 0.28)
    popularity_bonus = 1 + min(movie.tmdb_popularity / 220, 0.35)
    opening = (analytics.predicted_opening_weekend_usd if analytics else 12_000_000.0) * franchise_bonus * rating_bonus
    total = (analytics.predicted_domestic_total_usd if analytics else opening * 2.8) * popularity_bonus
    confidence = min(0.91, 0.46 + min(movie.tmdb_popularity / 150, 0.22) + min(rating / 25, 0.2))
    snapshot = MoviePredictionSnapshot(
        movie_id=movie.id,
        snapshot_at=datetime.utcnow(),
        predicted_opening_weekend_usd=round(opening, 2),
        predicted_domestic_total_usd=round(total, 2),
        confidence_score=round(confidence, 2),
        feature_version="bootstrap-feature-v1",
        model_version="rule-bootstrap-v1",
    )
    db.add(snapshot)
    return True


def _ensure_summary_snapshot(db: Session, movie: Movie) -> bool:
    existing = db.scalar(select(MovieSummarySnapshot.id).where(MovieSummarySnapshot.movie_id == movie.id).limit(1))
    if existing is not None:
        return False

    enrichment = get_enrichment(movie)
    omdb = fetch_movie_metadata(movie) or {}
    cast_text = ", ".join(enrichment.get("cast", [])[:3]) or "the lead cast"
    audience_summary = (
        f"Audience conversation around {movie.title} is currently anchored by {cast_text}, "
        f"{movie.status} timing, and the title's trailer momentum across social platforms."
    )
    critic_summary = (
        f"Critical context is being framed through {omdb.get('imdb_rating') or 'early'} rating signals, "
        f"{omdb.get('rotten_tomatoes') or 'limited review coverage'}, and comparisons to similar genre peers."
    )
    themes = [theme for theme in [enrichment.get("franchise"), *movie.genres[:3], *enrichment.get("studios", [])[:1]] if theme]
    snapshot = MovieSummarySnapshot(
        movie_id=movie.id,
        snapshot_at=datetime.utcnow(),
        audience_summary=audience_summary,
        critic_summary=critic_summary,
        key_themes=", ".join(themes[:5]),
        model_version="editorial-bootstrap-v1",
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
