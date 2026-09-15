from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from datetime import datetime
from statistics import mean

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.movie import Movie
from app.repositories import movies as movie_repository
from app.services.omdb import fetch_movie_metadata
from app.services.tmdb import _tmdb_get


def fetch_reviews_for_movie(db: Session, movie_id: int) -> list[dict]:
    movie = movie_repository.get_movie_by_id(db, movie_id)
    if movie is None or not movie.tmdb_id or not settings.tmdb_api_configured:
        return _critic_aggregate_only(movie) if movie is not None else []

    reviews: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for page in range(1, 6):
        try:
            payload = _tmdb_get(f"movie/{movie.tmdb_id}/reviews", page=page)
        except RuntimeError:
            break
        results = payload.get("results", [])
        if not results:
            break

        for item in results:
            author = (item.get("author") or "Unknown").strip()
            content = (item.get("content") or "").strip()
            created_raw = item.get("created_at")
            created_at = _parse_datetime(created_raw)
            if not content or created_at is None:
                continue

            key = (author.lower(), created_at.date().isoformat())
            if key in seen:
                continue
            seen.add(key)
            reviews.append(
                {
                    "author": author,
                    "content": content,
                    "created_at": created_at,
                    "source": "tmdb",
                }
            )

    for synthetic in _critic_aggregate_only(movie):
        key = (synthetic["author"].lower(), synthetic["created_at"].date().isoformat())
        if key in seen:
            continue
        seen.add(key)
        reviews.append(synthetic)

    reviews.sort(key=lambda item: item["created_at"])
    return reviews


def analyze_sentiment(reviews: list[dict]) -> list[dict]:
    if not reviews:
        return []

    if settings.USE_LIGHTWEIGHT_SENTIMENT:
        analyzer = _vader_analyzer()
        return [_score_with_vader(analyzer, review) for review in reviews]

    pipeline = _transformer_pipeline()
    return [_score_with_transformer(pipeline, review) for review in reviews]


def build_sentiment_timeline(reviews: list[dict]) -> dict:
    if not reviews:
        return {
            "timeline": [],
            "overall_sentiment": 0.0,
            "total_reviews": 0,
            "sentiment_trend": "stable",
            "positive_pct": 0,
            "neutral_pct": 0,
            "negative_pct": 0,
        }

    buckets: dict[str, list[dict]] = defaultdict(list)
    for review in reviews:
        week_start = _week_start(review["created_at"])
        buckets[week_start.isoformat()].append(review)

    timeline = []
    total_positive = 0
    total_neutral = 0
    total_negative = 0

    for week in sorted(buckets):
        items = buckets[week]
        avg_sentiment = round(mean(item["sentiment_score"] for item in items), 3)
        review_count = len(items)
        positive_count = sum(item["sentiment_label"] == "positive" for item in items)
        neutral_count = sum(item["sentiment_label"] == "neutral" for item in items)
        negative_count = sum(item["sentiment_label"] == "negative" for item in items)
        total_positive += positive_count
        total_neutral += neutral_count
        total_negative += negative_count
        timeline.append(
            {
                "week": week,
                "avg_sentiment": avg_sentiment,
                "review_count": review_count,
                "positive_pct": round((positive_count / review_count) * 100) if review_count else 0,
                "negative_pct": round((negative_count / review_count) * 100) if review_count else 0,
                "neutral_pct": round((neutral_count / review_count) * 100) if review_count else 0,
            }
        )

    overall_sentiment = round(mean(item["sentiment_score"] for item in reviews), 3)
    total_reviews = len(reviews)
    first = timeline[0]["avg_sentiment"]
    last = timeline[-1]["avg_sentiment"]
    delta = last - first
    if delta >= 0.1:
        trend = "improving"
    elif delta <= -0.1:
        trend = "declining"
    else:
        trend = "stable"

    return {
        "timeline": timeline,
        "overall_sentiment": overall_sentiment,
        "total_reviews": total_reviews,
        "sentiment_trend": trend,
        "positive_pct": round((total_positive / total_reviews) * 100) if total_reviews else 0,
        "neutral_pct": round((total_neutral / total_reviews) * 100) if total_reviews else 0,
        "negative_pct": round((total_negative / total_reviews) * 100) if total_reviews else 0,
    }


def refresh_review_sentiments_for_movie(db: Session, movie_id: int) -> dict:
    reviews = fetch_reviews_for_movie(db, movie_id)
    existing = {
        (item.author.lower(), item.created_at.isoformat(), item.source): item
        for item in movie_repository.list_review_sentiments(db, movie_id)
        if item.analyzed_at is not None
    }
    pending_reviews = [
        review
        for review in reviews
        if (review["author"].lower(), review["created_at"].isoformat(), review["source"]) not in existing
    ]
    analyzed = analyze_sentiment(pending_reviews)
    created = movie_repository.upsert_review_sentiments(db, movie_id, analyzed)
    stored = movie_repository.list_review_sentiments(db, movie_id)
    return {
        "fetched_reviews": len(reviews),
        "stored_reviews": len(stored),
        "new_reviews": created,
        "timeline": build_sentiment_timeline(
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
        ),
    }


def _critic_aggregate_only(movie: Movie | None) -> list[dict]:
    return []  # Aggregate scores are not authored review text.


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _week_start(value: datetime) -> datetime:
    start = value.date()
    return datetime.combine(start.fromordinal(start.toordinal() - start.weekday()), datetime.min.time())


@lru_cache(maxsize=1)
def _vader_analyzer():
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    return SentimentIntensityAnalyzer()


@lru_cache(maxsize=1)
def _transformer_pipeline():
    from transformers import pipeline

    return pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment")


def _score_with_vader(analyzer, review: dict) -> dict:
    text = _truncate_for_model(review["content"])
    scores = analyzer.polarity_scores(text)
    compound = float(scores["compound"])
    if compound >= 0.2:
        label = "positive"
    elif compound <= -0.2:
        label = "negative"
    else:
        label = "neutral"
    confidence = max(scores["pos"], scores["neu"], scores["neg"])
    return {
        **review,
        "content": text,
        "sentiment_score": round(compound, 4),
        "sentiment_label": label,
        "confidence": round(float(confidence), 4),
    }


def _score_with_transformer(sentiment_pipeline, review: dict) -> dict:
    text = _truncate_for_model(review["content"])
    result = sentiment_pipeline(text, truncation=True, max_length=512)[0]
    label_map = {"LABEL_2": "positive", "LABEL_1": "neutral", "LABEL_0": "negative"}
    sentiment_label = label_map.get(result["label"], "neutral")
    signed_score = float(result["score"])
    if sentiment_label == "negative":
        signed_score *= -1
    elif sentiment_label == "neutral":
        signed_score = 0.0
    return {
        **review,
        "content": text,
        "sentiment_score": round(max(-1.0, min(1.0, signed_score)), 4),
        "sentiment_label": sentiment_label,
        "confidence": round(float(result["score"]), 4),
    }


def _truncate_for_model(content: str) -> str:
    tokens = content.split()
    if len(tokens) <= 512:
        return content
    return " ".join(tokens[:512])
