from __future__ import annotations

from app.services.provider_metadata import normalize_metadata

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai import MovieDiscussion
from app.models.movie import Movie, MovieAnalytics
from app.repositories import movies as movie_repository
from app.services.hype_calculator import HypeCalculator

YOUTUBE_VIDEOS_ENDPOINT = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_COMMENTS_ENDPOINT = "https://www.googleapis.com/youtube/v3/commentThreads"
POSITIVE_TERMS = {
    "amazing", "awesome", "best", "brilliant", "epic", "excellent", "fire", "fun",
    "goat", "great", "hype", "iconic", "impressive", "incredible", "love", "loved",
    "masterpiece", "perfect", "phenomenal", "promising", "strong", "stunning",
}
NEGATIVE_TERMS = {
    "awful", "bad", "boring", "cheap", "confusing", "cringe", "disappointing", "flat",
    "hate", "hated", "mess", "mid", "poor", "rough", "terrible", "trash", "weak", "worse",
    "worst",
}


@dataclass
class RefreshResult:
    refreshed_movies: int = 0
    skipped_movies: int = 0
    failed_movies: int = 0
    skipped_reasons: list[str] | None = None
    failed_reasons: list[str] | None = None

    def __post_init__(self) -> None:
        if self.skipped_reasons is None:
            self.skipped_reasons = []
        if self.failed_reasons is None:
            self.failed_reasons = []


def extract_video_id(trailer_url: str | None) -> str | None:
    if not trailer_url:
        return None

    parsed = urlparse(trailer_url)
    host = parsed.netloc.lower()

    if host in {"youtu.be", "www.youtu.be"}:
        candidate = parsed.path.strip("/").split("/")[0]
        return candidate if _looks_like_video_id(candidate) else None

    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [None])[0]
            return candidate if _looks_like_video_id(candidate) else None

        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[0] in {"embed", "shorts", "live"}:
            candidate = path_parts[1]
            return candidate if _looks_like_video_id(candidate) else None

    return None


def refresh_all_movie_analytics(db: Session) -> RefreshResult:
    movies = movie_repository.list_movies(db)
    return _refresh_movies(db, movies)


def refresh_movie_analytics(db: Session, movie_id: int) -> RefreshResult:
    movie = movie_repository.get_movie_by_id(db, movie_id)
    if movie is None:
        return RefreshResult(failed_movies=1, failed_reasons=[f"Movie {movie_id} not found"])
    return _refresh_movies(db, [movie])


def _refresh_movies(db: Session, movies: list[Movie]) -> RefreshResult:
    result = RefreshResult()

    if not settings.youtube_api_configured:
        result.skipped_movies = len(movies)
        result.skipped_reasons.append("YOUTUBE_API_KEY is not configured")
        return result

    analytics_by_video_id: dict[str, list[MovieAnalytics]] = {}
    for movie in movies:
        analytics = movie_repository.get_movie_analytics(db, movie.id)
        if analytics is None:
            result.failed_movies += 1
            result.failed_reasons.append(f"{movie.title}: latest analytics snapshot is missing")
            continue

        video_id = extract_video_id(analytics.trailer_url)
        if video_id is None:
            result.skipped_movies += 1
            result.skipped_reasons.append(f"{movie.title}: trailer_url does not contain a supported YouTube video id")
            continue

        analytics_by_video_id.setdefault(video_id, []).append(analytics)

    if not analytics_by_video_id:
        return result

    try:
        video_stats = _fetch_video_statistics(list(analytics_by_video_id))
    except RuntimeError as exc:
        result.failed_movies += sum(len(items) for items in analytics_by_video_id.values())
        result.failed_reasons.append(str(exc))
        return result

    now = datetime.utcnow()
    for video_id, analytics_entries in analytics_by_video_id.items():
        stats = video_stats.get(video_id)
        if stats is None:
            result.skipped_movies += len(analytics_entries)
            for analytics in analytics_entries:
                result.skipped_reasons.append(f"{analytics.movie.title}: video statistics were not returned by YouTube")
            continue

        comments = _fetch_video_comments(video_id)
        for analytics in analytics_entries:
            analytics.youtube_views = stats["view_count"]
            analytics.youtube_likes = stats["like_count"]
            analytics.youtube_comments = stats["comment_count"]
            analytics.buzz_score = _recalculate_buzz_score(analytics)
            analytics.hype_score = _recalculate_hype_score(analytics)
            analytics.last_updated = now
            _record_observation(db, analytics)
            _sync_youtube_comments(db, analytics.movie, video_id, comments)
            result.refreshed_movies += 1

    db.commit()
    return result


def _fetch_video_statistics(video_ids: list[str]) -> dict[str, dict[str, int]]:
    batches = [video_ids[index:index + 50] for index in range(0, len(video_ids), 50)]
    aggregated: dict[str, dict[str, int]] = {}

    for batch in batches:
        query = (
            f"{YOUTUBE_VIDEOS_ENDPOINT}?"
            f"{urlencode({
                'part': 'statistics',
                'id': ','.join(batch),
                'fields': 'items(id,statistics(viewCount,likeCount,commentCount))',
                'key': settings.YOUTUBE_API_KEY,
            })}"
        )
        try:
            with urlopen(query, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"YouTube API request failed with HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"YouTube API request failed: {exc.reason}") from exc

        for item in payload.get("items", []):
            video_id = item.get("id")
            statistics = item.get("statistics", {})
            if not video_id:
                continue
            aggregated[video_id] = {
                "view_count": _safe_int(statistics.get("viewCount")),
                "like_count": _safe_int(statistics.get("likeCount")),
                "comment_count": _safe_int(statistics.get("commentCount")),
            }

    return aggregated


def _fetch_video_comments(video_id: str, limit: int = 8) -> list[dict[str, Any]]:
    query = (
        f"{YOUTUBE_COMMENTS_ENDPOINT}?"
        f"{urlencode({
            'part': 'snippet',
            'videoId': video_id,
            'maxResults': min(limit, 20),
            'order': 'relevance',
            'textFormat': 'plainText',
            'key': settings.YOUTUBE_API_KEY,
        })}"
    )
    try:
        with urlopen(query, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError):
        return []

    comments: list[dict[str, Any]] = []
    for item in payload.get("items", []):
        snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
        comment_id = item.get("id")
        text = (snippet.get("textDisplay") or "").strip()
        if not isinstance(comment_id, str) or not text:
            continue
        comments.append(
            {
                "id": comment_id,
                "author": snippet.get("authorDisplayName"),
                "text": text,
                "like_count": _safe_int(snippet.get("likeCount")),
                "published_at": snippet.get("publishedAt"),
                "url": f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}",
                "sentiment": _score_comment_sentiment(text),
            }
        )
    return comments


def _sync_youtube_comments(db: Session, movie: Movie, video_id: str, comments: list[dict[str, Any]]) -> None:
    for index, comment in enumerate(comments, start=1):
        external_id = f"youtube-{movie.id}-{video_id}-{comment['id']}"
        existing = next((item for item in movie.discussions if item.external_id == external_id), None)
        body = comment["text"]
        title = f"YouTube viewer reaction #{index}"
        payload = json.dumps(
            {
                "video_id": video_id,
                "like_count": comment["like_count"],
                "sentiment": comment["sentiment"],
            }
        )
        if existing is None:
            db.add(
                MovieDiscussion(
                    movie_id=movie.id,
                    source="youtube",
                    external_id=external_id,
                    title=title,
                    body=body,
                    author=comment["author"],
                    engagement_score=float(comment["like_count"]),
                    url=comment["url"],
                    raw_payload=payload,
                    created_at=datetime.fromisoformat(comment["published_at"].replace("Z", "+00:00")).replace(tzinfo=None) if comment.get("published_at") else datetime.utcnow(),
                )
            )
            continue

        existing.title = title
        existing.body = body
        existing.author = comment["author"]
        existing.engagement_score = float(comment["like_count"])
        existing.url = comment["url"]
        existing.raw_payload = payload


def _recalculate_buzz_score(analytics: MovieAnalytics) -> float:
    payload = {
        "youtube_views": analytics.youtube_views,
        "youtube_comments": analytics.youtube_comments,
        "google_trends_score": analytics.google_trends_score,
        "twitter_mentions": analytics.x_mentions,
        "reddit_mentions": analytics.reddit_mentions,
        "momentum_score": analytics.momentum_score,
    }
    return HypeCalculator.calculate_buzz_score(payload)


def _recalculate_hype_score(analytics: MovieAnalytics) -> float:
    payload = {
        "youtube_views": analytics.youtube_views,
        "youtube_likes": analytics.youtube_likes,
        "youtube_comments": analytics.youtube_comments,
        "google_trends_score": analytics.google_trends_score,
        "twitter_mentions": analytics.x_mentions,
        "reddit_mentions": analytics.reddit_mentions,
        "sentiment_score": analytics.sentiment_score,
        "momentum_score": analytics.momentum_score,
    }
    release_date = datetime.combine(analytics.movie.release_date, datetime.min.time())
    return HypeCalculator.calculate_hype_score(payload, release_date)


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _looks_like_video_id(candidate: str | None) -> bool:
    if not candidate:
        return False
    return len(candidate) == 11 and all(character.isalnum() or character in {"-", "_"} for character in candidate)


def _score_comment_sentiment(text: str) -> str:
    words = {
        token.strip(".,!?;:'\"()[]{}").lower()
        for token in text.split()
        if token.strip()
    }
    positive = len(words & POSITIVE_TERMS)
    negative = len(words & NEGATIVE_TERMS)
    if positive > negative:
        return "positive"
    if negative > positive:
        return "negative"
    return "neutral"


def _record_observation(db: Session, analytics: MovieAnalytics) -> None:
    observed = analytics.last_updated
    analytics.snapshot_date = observed.date()
    movie = analytics.movie
    movie.provider_metadata = {
        **normalize_metadata(movie.provider_metadata),
        "youtube_observation": {"verified_at": observed.isoformat(), "source_url": analytics.trailer_url},
    }
    label = f"observed-{observed.date().isoformat()}"
    snapshot = next((a for a in movie.analytics_snapshots if a.snapshot_label == label), None)
    if snapshot is None:
        snapshot = MovieAnalytics(snapshot_label=label)
        movie.analytics_snapshots.append(snapshot)
        db.add(snapshot)
    for column in MovieAnalytics.__table__.columns:
        if column.name not in {"id", "movie_id", "snapshot_label"}:
            setattr(snapshot, column.name, getattr(analytics, column.name))
