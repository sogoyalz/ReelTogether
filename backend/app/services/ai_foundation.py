from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta

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
from app.services.prediction_model import apply_prediction_snapshot, build_prediction_payload
from app.services.review_analysis import (
    analyze_review_landscape,
    extract_top_themes,
    sentiment_counts_from_discussions,
)


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
    movie = db.scalar(select(Movie).where(Movie.id == movie_id))
    if movie is None:
        return None
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
    feature = db.scalar(
        select(MovieFeatureSnapshot)
        .where(MovieFeatureSnapshot.movie_id == movie_id)
        .order_by(MovieFeatureSnapshot.snapshot_at.desc())
    )
    discussions = list(
        db.scalars(
            select(MovieDiscussion)
            .where(MovieDiscussion.movie_id == movie_id)
            .order_by(MovieDiscussion.engagement_score.desc(), MovieDiscussion.created_at.desc())
            .limit(12)
        ).all()
    )

    if not sentiment or not prediction or not summary or not feature:
        return None

    enrichment = get_enrichment(movie)
    omdb = fetch_movie_metadata(movie) or {}
    review_landscape = analyze_review_landscape(movie, discussions, enrichment, omdb)
    prediction_payload = build_prediction_payload(
        movie=movie,
        analytics=_latest_analytics(movie),
        feature_snapshot=feature,
        sentiment_snapshot=sentiment,
        enrichment=enrichment,
    )

    return {
        "sentiment": sentiment,
        "prediction": prediction,
        "summary": summary,
        "public_opinion": build_public_opinion(discussions),
        "critic_vs_audience": review_landscape,
        "prediction_payload": prediction_payload,
        "discussions": discussions,
    }


def build_public_opinion(discussions: list[MovieDiscussion]) -> dict:
    audience_discussions = [discussion for discussion in discussions if discussion.source in {"reddit", "youtube", "audience", "social"}]
    if not audience_discussions:
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

    for discussion in audience_discussions:
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
    enrichment = get_enrichment(movie)
    themes = movie.genres[:2] + ([enrichment.get("franchise")] if enrichment.get("franchise") else [])
    templates = [
        ("reddit", f"Early audience reaction to {movie.title}", "Fans are focusing on the scale, cast, and whether the story can match the hype."),
        ("reddit", f"Is {movie.title} going to overperform?", "Discussion is centered on trailer momentum, franchise pull, and release timing."),
        ("youtube", f"{movie.title} trailer comment summary", "Viewers are reacting to the visuals, tone, and standout cast moments from the trailer."),
        ("critic", f"{movie.title} critic consensus", "Reviewers are weighing the direction, writing, performances, pacing, and overall craft."),
        ("critic", f"{movie.title} awards and prestige read", "Press coverage is centered on awards potential, thematic depth, and whether the film has staying power."),
    ]
    dirty = False
    for index, (source, title, body) in enumerate(templates, start=1):
        external_id = f"{source}-{movie.slug}-{index}"
        existing = db.scalar(
            select(MovieDiscussion).where(MovieDiscussion.external_id == external_id).limit(1)
        )
        payload = json.dumps(
            {
                "movie": movie.slug,
                "source": source,
                "seeded": True,
                "sentiment": "positive" if source == "critic" and movie.tmdb_popularity > 80 else "neutral",
            }
        )
        text = f"{body} Key themes include {', '.join([theme for theme in themes if theme][:3]) or 'franchise potential'}."
        if existing is not None:
            existing.title = title
            existing.body = text
            existing.author = f"{source}_editorial_{index}"
            existing.engagement_score = round(55 + movie.tmdb_popularity * 0.8 - index * 2, 2)
            existing.url = f"https://example.com/{source}/{movie.slug}/{index}"
            existing.raw_payload = payload
            dirty = True
            continue
        discussion = MovieDiscussion(
            movie_id=movie.id,
            source=source,
            external_id=external_id,
            title=title,
            body=text,
            author=f"{source}_editorial_{index}",
            engagement_score=round(55 + movie.tmdb_popularity * 0.8 - index * 2, 2),
            url=f"https://example.com/{source}/{movie.slug}/{index}",
            created_at=datetime.utcnow() - timedelta(hours=index * 7),
            raw_payload=payload,
        )
        db.add(discussion)
        dirty = True
    return dirty


def _ensure_sentiment_snapshot(db: Session, movie: Movie) -> bool:
    snapshot = db.scalar(
        select(MovieSentimentSnapshot)
        .where(MovieSentimentSnapshot.movie_id == movie.id)
        .order_by(MovieSentimentSnapshot.snapshot_at.desc())
        .limit(1)
    )
    if snapshot is None:
        snapshot = MovieSentimentSnapshot(movie_id=movie.id)
        db.add(snapshot)

    discussions = list(
        db.scalars(
            select(MovieDiscussion).where(MovieDiscussion.movie_id == movie.id)
        ).all()
    )
    counts = sentiment_counts_from_discussions(discussions)
    sample_size = sum(counts.values()) or 1
    snapshot.snapshot_at = datetime.utcnow()
    snapshot.positive_count = counts["positive"]
    snapshot.neutral_count = counts["neutral"]
    snapshot.negative_count = counts["negative"]
    snapshot.sentiment_score = round((counts["positive"] - counts["negative"]) / sample_size, 2)
    snapshot.sample_size = sample_size
    snapshot.model_version = "hybrid-nlp-v2"
    return True


def _ensure_feature_snapshot(db: Session, movie: Movie) -> bool:
    snapshot = db.scalar(
        select(MovieFeatureSnapshot)
        .where(MovieFeatureSnapshot.movie_id == movie.id)
        .order_by(MovieFeatureSnapshot.snapshot_at.desc())
        .limit(1)
    )
    if snapshot is None:
        snapshot = MovieFeatureSnapshot(movie_id=movie.id)
        db.add(snapshot)
    analytics = _latest_analytics(movie)
    omdb = fetch_movie_metadata(movie) or {}
    views = analytics.youtube_views if analytics else 0
    likes = analytics.youtube_likes if analytics else 0
    comments = analytics.youtube_comments if analytics else 0
    snapshot.snapshot_at = datetime.utcnow()
    snapshot.release_days_until = (movie.release_date - date.today()).days
    snapshot.trailer_views = views
    snapshot.likes_to_views_ratio = round((likes / views) if views else 0.0, 4)
    snapshot.comments_to_views_ratio = round((comments / views) if views else 0.0, 4)
    snapshot.reddit_mentions = analytics.reddit_mentions if analytics else 0
    snapshot.social_mentions = (analytics.x_mentions + analytics.reddit_mentions) if analytics else 0
    snapshot.tmdb_popularity = movie.tmdb_popularity
    snapshot.imdb_rating = _parse_float(omdb.get("imdb_rating"))
    snapshot.sentiment_score = analytics.sentiment_score if analytics else 0.0
    snapshot.feature_version = "hybrid-feature-v2"
    return True


def _ensure_prediction_snapshot(db: Session, movie: Movie) -> bool:
    snapshot = db.scalar(
        select(MoviePredictionSnapshot)
        .where(MoviePredictionSnapshot.movie_id == movie.id)
        .order_by(MoviePredictionSnapshot.snapshot_at.desc())
        .limit(1)
    )
    if snapshot is None:
        snapshot = MoviePredictionSnapshot(movie_id=movie.id)
        db.add(snapshot)

    analytics = _latest_analytics(movie)
    feature_snapshot = db.scalar(
        select(MovieFeatureSnapshot)
        .where(MovieFeatureSnapshot.movie_id == movie.id)
        .order_by(MovieFeatureSnapshot.snapshot_at.desc())
        .limit(1)
    )
    sentiment_snapshot = db.scalar(
        select(MovieSentimentSnapshot)
        .where(MovieSentimentSnapshot.movie_id == movie.id)
        .order_by(MovieSentimentSnapshot.snapshot_at.desc())
        .limit(1)
    )
    if feature_snapshot is None:
        return False

    payload = build_prediction_payload(
        movie=movie,
        analytics=analytics,
        feature_snapshot=feature_snapshot,
        sentiment_snapshot=sentiment_snapshot,
        enrichment=get_enrichment(movie),
    )
    snapshot.snapshot_at = datetime.utcnow()
    apply_prediction_snapshot(
        snapshot,
        payload,
        feature_version="hybrid-feature-v2",
        model_version="hybrid-forecast-v2",
    )
    return True


def _ensure_summary_snapshot(db: Session, movie: Movie) -> bool:
    snapshot = db.scalar(
        select(MovieSummarySnapshot)
        .where(MovieSummarySnapshot.movie_id == movie.id)
        .order_by(MovieSummarySnapshot.snapshot_at.desc())
        .limit(1)
    )
    if snapshot is None:
        snapshot = MovieSummarySnapshot(movie_id=movie.id, audience_summary="", critic_summary="", key_themes="")
        db.add(snapshot)

    discussions = list(
        db.scalars(
            select(MovieDiscussion).where(MovieDiscussion.movie_id == movie.id)
        ).all()
    )
    enrichment = get_enrichment(movie)
    omdb = fetch_movie_metadata(movie) or {}
    review_landscape = analyze_review_landscape(movie, discussions, enrichment, omdb)
    themes = extract_top_themes(
        discussions,
        [theme for theme in [enrichment.get("franchise"), *movie.genres[:3], *enrichment.get("studios", [])[:1]] if theme],
        limit=5,
    )
    snapshot.snapshot_at = datetime.utcnow()
    snapshot.audience_summary = review_landscape["audience"].summary
    snapshot.critic_summary = review_landscape["critics"].summary
    snapshot.key_themes = ", ".join(themes[:5])
    snapshot.model_version = "hybrid-review-v2"
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
