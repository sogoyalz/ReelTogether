from __future__ import annotations

from app.services.provider_metadata import normalize_metadata

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from math import log1p
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.cache import ExpiringMap
from app.models.movie import Movie, MovieAnalytics
from app.services.hype_calculator import HypeCalculator

TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w780"
_DETAIL_CACHE = ExpiringMap()
_GENRE_CACHE: dict[int, str] | None = None


@dataclass
class TmdbSyncResult:
    synced_movies: int = 0
    updated_movies: int = 0
    created_movies: int = 0
    failed_movies: int = 0
    errors: list[str] | None = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


DEFAULT_FEED_PATHS = [
    "movie/popular",
    "movie/upcoming",
    "movie/now_playing",
    "movie/top_rated",
]


def sync_tmdb_catalog(
    db: Session,
    pages_per_feed: int = 2,
    *,
    target_total_movies: int | None = None,
    feed_paths: list[str] | None = None,
    include_watch_providers: bool = True,
    include_full_details: bool = True,
) -> TmdbSyncResult:
    result = TmdbSyncResult()
    if not settings.tmdb_api_configured:
        result.errors.append("TMDB_API_KEY is not configured")
        return result

    active_feed_paths = feed_paths or DEFAULT_FEED_PATHS
    seen_ids: set[int] = set()
    used_slugs = set(db.scalars(select(Movie.slug)).all())
    projected_total = len(used_slugs)
    genre_map = _tmdb_genre_map() if not include_full_details else None

    for path in active_feed_paths:
        for page in range(1, pages_per_feed + 1):
            if target_total_movies is not None and projected_total >= target_total_movies:
                db.commit()
                return result
            try:
                payload = _tmdb_get(path, page=page)
            except RuntimeError as exc:
                result.errors.append(str(exc))
                continue

            for item in payload.get("results", []):
                movie_id = item.get("id")
                if not isinstance(movie_id, int) or movie_id in seen_ids:
                    continue
                seen_ids.add(movie_id)

                try:
                    if not include_full_details:
                        created = _upsert_movie_summary(db, item, genre_map or {}, result, used_slugs=used_slugs)
                        if created:
                            projected_total += 1
                        if target_total_movies is not None and projected_total >= target_total_movies:
                            db.commit()
                            return result
                        continue
                    details = _tmdb_get(
                        f"movie/{movie_id}",
                        append_to_response="videos,credits,images",
                    )
                    providers_payload = (
                        _tmdb_get(f"movie/{movie_id}/watch/providers")
                        if include_watch_providers
                        else None
                    )
                    _DETAIL_CACHE[movie_id] = _build_enrichment_payload(details, providers_payload)
                    created = _upsert_movie(db, details, result, used_slugs=used_slugs)
                    if created:
                        projected_total += 1
                except RuntimeError as exc:
                    result.failed_movies += 1
                    result.errors.append(f"{item.get('title', movie_id)}: {exc}")

                if target_total_movies is not None and projected_total >= target_total_movies:
                    db.commit()
                    return result

    db.commit()
    return result


def sync_tmdb_search_results(db: Session, query: str, limit: int = 8) -> TmdbSyncResult:
    result = TmdbSyncResult()
    if not settings.tmdb_api_configured or not query.strip():
        return result

    try:
        payload = _tmdb_get("search/movie", query=query.strip())
    except RuntimeError as exc:
        result.errors.append(str(exc))
        return result

    for item in payload.get("results", [])[:limit]:
        movie_id = item.get("id")
        if not isinstance(movie_id, int):
            continue
        try:
            details = _tmdb_get(f"movie/{movie_id}", append_to_response="videos,credits,images")
            providers_payload = _tmdb_get(f"movie/{movie_id}/watch/providers")
            _DETAIL_CACHE[movie_id] = _build_enrichment_payload(details, providers_payload)
            _upsert_movie(db, details, result)
        except RuntimeError as exc:
            result.failed_movies += 1
            result.errors.append(f"{item.get('title', movie_id)}: {exc}")

    db.commit()
    return result


def get_tmdb_movie_enrichment(movie: Movie, allow_network: bool = False) -> dict | None:
    if movie.enrichment_data:
        return movie.enrichment_data
    if not settings.tmdb_api_configured or not movie.tmdb_id:
        return None

    # Offline catalog readers must use persisted data consistently across workers.
    # A detail request's process-local cache must not change browse filters/facets.
    if not allow_network:
        return None

    cached = _DETAIL_CACHE.get(movie.tmdb_id)
    if cached is not None:
        return cached

    try:
        details = _tmdb_get("movie/{movie_id}".format(movie_id=movie.tmdb_id), append_to_response="videos,credits,images")
        providers_payload = _tmdb_get(f"movie/{movie.tmdb_id}/watch/providers")
    except RuntimeError:
        return None

    result = _build_enrichment_payload(details, providers_payload)
    _DETAIL_CACHE[movie.tmdb_id] = result
    return result


def _upsert_movie(db: Session, details: dict, result: TmdbSyncResult, *, used_slugs: set[str] | None = None) -> bool:
    tmdb_id = details.get("id")
    title = (details.get("title") or "").strip()
    release_date = _parse_date(details.get("release_date"))
    if not isinstance(tmdb_id, int) or not title or release_date is None:
        result.failed_movies += 1
        result.errors.append(f"Skipped invalid TMDB payload: {tmdb_id or title or 'unknown'}")
        return False

    db.flush()  # Make pending imports visible before resolving IDs and slugs.
    slug = _slugify(title)
    existing = db.scalar(select(Movie).where(Movie.tmdb_id == tmdb_id))
    slug = _resolve_slug_conflict(db, slug, tmdb_id, existing, used_slugs=used_slugs)

    genres = [genre["name"] for genre in details.get("genres", []) if genre.get("name")]
    movie = existing or Movie(
        tmdb_id=tmdb_id,
        slug=slug,
        title=title,
        release_date=release_date,
        status=_derive_status(release_date),
        poster_url=None,
        backdrop_url=None,
        overview=None,
        genres=[],
        tmdb_popularity=0,
    )

    metadata = normalize_metadata(movie.provider_metadata)
    if isinstance(details.get("runtime"), int) and details["runtime"] > 0:
        metadata["runtime"] = f"{details['runtime']} min"
    if details.get("original_language"):
        metadata["original_language"] = details["original_language"]
    movie.provider_metadata = metadata
    movie.enrichment_data = _DETAIL_CACHE.get(tmdb_id) or movie.enrichment_data or {}
    movie.tmdb_id = tmdb_id
    movie.slug = slug
    movie.title = title
    movie.release_date = release_date
    movie.status = _derive_status(release_date)
    movie.poster_url = _image_url(details.get("poster_path"))
    movie.backdrop_url = _image_url(details.get("backdrop_path"))
    movie.overview = details.get("overview") or None
    movie.genres = genres
    movie.tmdb_popularity = float(details.get("popularity") or 0.0)

    analytics = next((snapshot for snapshot in movie.analytics_snapshots if snapshot.snapshot_label == "latest"), None)
    if analytics is None:
        analytics = MovieAnalytics(snapshot_label="latest")
        movie.analytics_snapshots.append(analytics)

    _populate_analytics(movie, analytics, details)

    if existing is None:
        db.add(movie)
        result.created_movies += 1
        created = True
    else:
        result.updated_movies += 1
        created = False
    if used_slugs is not None:
        used_slugs.add(movie.slug)
    from app.services.omdb import fetch_movie_metadata
    metadata = fetch_movie_metadata(movie)
    if metadata:
        movie.provider_metadata = {**normalize_metadata(movie.provider_metadata), **metadata}
    result.synced_movies += 1
    return created


def _upsert_movie_summary(
    db: Session,
    item: dict,
    genre_map: dict[int, str],
    result: TmdbSyncResult,
    *,
    used_slugs: set[str] | None = None,
) -> bool:
    tmdb_id = item.get("id")
    title = (item.get("title") or "").strip()
    release_date = _parse_date(item.get("release_date"))
    if not isinstance(tmdb_id, int) or not title or release_date is None:
        result.failed_movies += 1
        result.errors.append(f"Skipped invalid TMDB summary payload: {tmdb_id or title or 'unknown'}")
        return False

    db.flush()  # Make pending imports visible before resolving IDs and slugs.
    slug = _slugify(title)
    existing = db.scalar(select(Movie).where(Movie.tmdb_id == tmdb_id))
    slug = _resolve_slug_conflict(db, slug, tmdb_id, existing, used_slugs=used_slugs)

    genres = [
        genre_map[genre_id]
        for genre_id in item.get("genre_ids", [])
        if isinstance(genre_id, int) and genre_id in genre_map
    ]
    movie = existing or Movie(
        tmdb_id=tmdb_id,
        slug=slug,
        title=title,
        release_date=release_date,
        status=_derive_status(release_date),
        poster_url=None,
        backdrop_url=None,
        overview=None,
        genres=[],
        tmdb_popularity=0,
    )

    movie.enrichment_data = _DETAIL_CACHE.get(tmdb_id) or movie.enrichment_data or {}
    movie.tmdb_id = tmdb_id
    movie.slug = slug
    movie.title = title
    movie.release_date = release_date
    movie.status = _derive_status(release_date)
    movie.poster_url = _image_url(item.get("poster_path"))
    movie.backdrop_url = _image_url(item.get("backdrop_path"))
    movie.overview = item.get("overview") or None
    movie.genres = genres
    movie.tmdb_popularity = float(item.get("popularity") or 0.0)

    analytics = next((snapshot for snapshot in movie.analytics_snapshots if snapshot.snapshot_label == "latest"), None)
    if analytics is None:
        analytics = MovieAnalytics(snapshot_label="latest")
        movie.analytics_snapshots.append(analytics)

    _populate_analytics(movie, analytics, {"popularity": item.get("popularity"), "videos": {"results": []}})

    if existing is None:
        db.add(movie)
        result.created_movies += 1
        created = True
    else:
        result.updated_movies += 1
        created = False
    if used_slugs is not None:
        used_slugs.add(movie.slug)
    from app.services.omdb import fetch_movie_metadata
    metadata = fetch_movie_metadata(movie)
    if metadata:
        movie.provider_metadata = {**normalize_metadata(movie.provider_metadata), **metadata}
    result.synced_movies += 1
    return created


def _populate_analytics(movie: Movie, analytics: MovieAnalytics, details: dict) -> None:
    if analytics.id is not None:
        trailer = _extract_trailer_url(details.get("videos", {}).get("results", []))
        if trailer:
            analytics.trailer_url = trailer
        return  # A catalog refresh must not replace observed analytics with estimates.
    popularity = float(details.get("popularity") or 0.0)
    release_date = movie.release_date
    trailer_url = _extract_trailer_url(details.get("videos", {}).get("results", []))
    days_until_release = (release_date - date.today()).days

    estimated_views = max(250_000, int((log1p(popularity + 1) * 1_250_000) * (1.4 if days_until_release > 0 else 1.1)))
    estimated_likes = max(10_000, int(estimated_views * 0.028))
    estimated_comments = max(1_500, int(estimated_views * 0.0017))
    google_trends = round(min(100.0, 35 + popularity * 1.15), 2)
    x_mentions = max(3_000, int(popularity * 2_200))
    reddit_mentions = max(900, int(popularity * 340))
    sentiment = 0.74 if movie.status == "released" else 0.78
    momentum = min(0.98, 0.48 + min(popularity / 100, 0.42))
    predicted_opening = max(8_000_000.0, float(popularity) * 1_650_000)
    predicted_total = predicted_opening * (3.1 if movie.status == "released" else 2.7)

    analytics_payload = {
        "youtube_views": estimated_views,
        "youtube_likes": estimated_likes,
        "youtube_comments": estimated_comments,
        "google_trends_score": google_trends,
        "twitter_mentions": x_mentions,
        "reddit_mentions": reddit_mentions,
        "sentiment_score": sentiment,
        "momentum_score": momentum,
    }

    analytics.snapshot_date = date.today()
    analytics.youtube_views = estimated_views
    analytics.youtube_likes = estimated_likes
    analytics.youtube_comments = estimated_comments
    analytics.google_trends_score = google_trends
    analytics.x_mentions = x_mentions
    analytics.reddit_mentions = reddit_mentions
    analytics.sentiment_score = sentiment
    analytics.sentiment_positive = 72 if movie.status == "released" else 69
    analytics.sentiment_neutral = 19
    analytics.sentiment_negative = 9 if movie.status == "released" else 12
    analytics.momentum_score = round(momentum, 2)
    analytics.buzz_score = HypeCalculator.calculate_buzz_score(analytics_payload)
    analytics.hype_score = HypeCalculator.calculate_hype_score(
        analytics_payload,
        datetime.combine(release_date, datetime.min.time()),
    )
    analytics.predicted_opening_weekend_usd = round(predicted_opening, 2)
    analytics.predicted_domestic_total_usd = round(predicted_total, 2)
    analytics.trailer_url = trailer_url
    analytics.last_updated = datetime.utcnow()


def _tmdb_get(path: str, **params) -> dict:
    query = urlencode({"api_key": settings.TMDB_API_KEY, **params})
    url = f"{TMDB_API_BASE}/{path}?{query}"
    try:
        with urlopen(url, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"TMDB request failed for {path} with HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"TMDB request failed for {path}: {exc.reason}") from exc


def _catalog_size(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(Movie)) or 0)


def _tmdb_genre_map() -> dict[int, str]:
    global _GENRE_CACHE
    if _GENRE_CACHE is not None:
        return _GENRE_CACHE

    payload = _tmdb_get("genre/movie/list")
    _GENRE_CACHE = {
        genre["id"]: genre["name"]
        for genre in payload.get("genres", [])
        if isinstance(genre.get("id"), int) and genre.get("name")
    }
    return _GENRE_CACHE


def _resolve_slug_conflict(
    db: Session,
    slug: str,
    tmdb_id: int,
    existing: Movie | None,
    *,
    used_slugs: set[str] | None = None,
) -> str:
    if used_slugs is not None and slug in used_slugs:
        if existing is not None and existing.slug == slug:
            return slug
        return f"{slug}-{tmdb_id}"

    owner = db.scalar(select(Movie).where(Movie.slug == slug))
    if owner is None:
        return slug
    if existing is not None and owner.id == existing.id:
        return slug
    if owner.tmdb_id == tmdb_id:
        return slug
    return f"{slug}-{tmdb_id}"


def _image_url(path: str | None) -> str | None:
    if not path:
        return None
    return f"{TMDB_IMAGE_BASE}{path}"


def _to_embed_url(trailer_url: str | None) -> str | None:
    if not trailer_url or "watch?v=" not in trailer_url:
        return None
    return trailer_url.replace("watch?v=", "embed/")


def _best_logo(logos: list[dict]) -> str | None:
    for logo in logos:
        file_path = logo.get("file_path")
        if file_path:
            return _image_url(file_path)
    return None


def _build_enrichment_payload(details: dict, providers_payload: dict | None = None) -> dict:
    crew = details.get("credits", {}).get("crew", [])
    cast = details.get("credits", {}).get("cast", [])
    videos = details.get("videos", {}).get("results", [])
    providers = (
        (providers_payload or {}).get("results", {})
        .get("US", {})
        .get("flatrate", [])
    )
    trailer_url = _extract_trailer_url(videos)
    return {
        "franchise": (details.get("belongs_to_collection") or {}).get("name"),
        "studios": [company["name"] for company in details.get("production_companies", []) if company.get("name")],
        "streaming_on": [provider["provider_name"] for provider in providers if provider.get("provider_name")],
        "cast": [person["name"] for person in cast[:6] if person.get("name")],
        "directors": [person["name"] for person in crew if person.get("job") == "Director" and person.get("name")],
        "writers": [
            person["name"]
            for person in crew
            if person.get("job") in {"Writer", "Screenplay", "Story"} and person.get("name")
        ][:5],
        "trailer_embed_url": _to_embed_url(trailer_url),
        "trailer_url": trailer_url,
        "logo_url": _best_logo(details.get("images", {}).get("logos", [])),
        "backdrops": [
            _image_url(image.get("file_path"))
            for image in details.get("images", {}).get("backdrops", [])[:6]
            if image.get("file_path")
        ],
    }


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    return date.fromisoformat(raw)


def _derive_status(release_date: date) -> str:
    today = date.today()
    if release_date < today:
        return "released"
    if release_date > today + timedelta(days=120):
        return "announced"
    return "upcoming"


def _extract_trailer_url(videos: list[dict]) -> str | None:
    for video in videos:
        if (
            video.get("site") == "YouTube"
            and video.get("type") == "Trailer"
            and isinstance(video.get("key"), str)
        ):
            return f"https://www.youtube.com/watch?v={video['key']}"

    for video in videos:
        if video.get("site") == "YouTube" and isinstance(video.get("key"), str):
            return f"https://www.youtube.com/watch?v={video['key']}"
    return None


def _slugify(value: str) -> str:
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", value.lower()))
