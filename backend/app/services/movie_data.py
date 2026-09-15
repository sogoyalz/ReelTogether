from __future__ import annotations

from datetime import date, datetime, timezone

from app.models.movie import Movie, MovieAnalytics
from app.services.mock_data import SEEDED_MOVIE_SLUGS
from app.services.prediction_model import is_non_theatrical_release, normalize_public_forecast

FieldSource = str


def build_movie_data_contract(
    movie: Movie,
    *,
    analytics: MovieAnalytics | None = None,
    enrichment: dict | None = None,
    omdb_metadata: dict | None = None,
    opening: float = 0.0,
    domestic: float = 0.0,
    confidence: float = 0.0,
    opening_low: float = 0.0,
    opening_high: float = 0.0,
    domestic_low: float = 0.0,
    domestic_high: float = 0.0,
) -> dict:
    enrichment = enrichment or {}
    omdb_metadata = omdb_metadata or {}

    canonical_status = derive_canonical_status(movie)
    catalog_source = _infer_catalog_source(movie)
    release_source = catalog_source
    forecast = normalize_public_forecast(
        movie,
        enrichment=enrichment,
        box_office=omdb_metadata.get("box_office"),
        opening=opening,
        domestic=domestic,
        confidence=confidence,
        opening_low=opening_low,
        opening_high=opening_high,
        domestic_low=domestic_low,
        domestic_high=domestic_high,
    )
    distribution_type = (
        "streaming-first"
        if is_non_theatrical_release(movie, enrichment=enrichment, box_office=omdb_metadata.get("box_office"))
        else "theatrical"
    )

    field_sources: dict[str, FieldSource] = {
        "title": catalog_source,
        "release_date": release_source,
        "status": "generated",
        "poster_url": catalog_source if movie.poster_url else "missing",
        "backdrop_url": catalog_source if movie.backdrop_url else "missing",
        "overview": catalog_source if movie.overview else "missing",
        "genres": catalog_source if movie.genres else "missing",
        "franchise": _enrichment_source(movie, enrichment, "franchise"),
        "studios": _enrichment_source(movie, enrichment, "studios"),
        "streaming_on": _enrichment_source(movie, enrichment, "streaming_on"),
        "cast": _enrichment_source(movie, enrichment, "cast"),
        "directors": _enrichment_source(movie, enrichment, "directors"),
        "writers": _enrichment_source(movie, enrichment, "writers"),
        "box_office_history": _enrichment_source(movie, enrichment, "box_office_history"),
        "imdb_rating": "sourced" if omdb_metadata.get("imdb_rating") else "missing",
        "rated": "sourced" if omdb_metadata.get("rated") else "missing",
        "runtime": "sourced" if omdb_metadata.get("runtime") else "missing",
        "rotten_tomatoes": "sourced" if omdb_metadata.get("rotten_tomatoes") else "missing",
        "box_office": "sourced" if omdb_metadata.get("box_office") else "missing",
        "awards": "sourced" if omdb_metadata.get("awards") else "missing",
        "metascore": "sourced" if omdb_metadata.get("metascore") else "missing",
        "imdb_votes": "sourced" if omdb_metadata.get("imdb_votes") else "missing",
        "trailer_url": "sourced" if analytics and analytics.trailer_url else "missing",
        "trailer_views": "estimated" if analytics and analytics.youtube_views else "missing",
        "youtube_likes": "estimated" if analytics and analytics.youtube_likes else "missing",
        "youtube_comments": "estimated" if analytics and analytics.youtube_comments else "missing",
        "google_trends_score": "estimated" if analytics and analytics.google_trends_score else "missing",
        "x_mentions": "estimated" if analytics and analytics.x_mentions else "missing",
        "reddit_mentions": "estimated" if analytics and analytics.reddit_mentions else "missing",
        "social_mentions": "estimated" if analytics and (analytics.x_mentions or analytics.reddit_mentions) else "missing",
        "sentiment_score": "estimated" if analytics and analytics.sentiment_score else "missing",
        "buzz_score": "estimated" if analytics and analytics.buzz_score else "missing",
        "hype_score": "estimated" if analytics and analytics.hype_score else "missing",
        "predicted_opening_weekend_usd": "generated" if forecast["forecast_is_public"] and forecast["predicted_opening_weekend_usd"] else "missing",
        "predicted_domestic_total_usd": "generated" if forecast["forecast_is_public"] and forecast["predicted_domestic_total_usd"] else "missing",
    }

    if (movie.provider_metadata or {}).get("youtube_observation"):
        for field in ("trailer_views", "youtube_likes", "youtube_comments"):
            field_sources[field] = "sourced"

    warnings = _build_warnings(
        movie,
        canonical_status=canonical_status,
        catalog_source=catalog_source,
        distribution_type=distribution_type,
        forecast=forecast,
        analytics=analytics,
        omdb_metadata=omdb_metadata,
    )
    data_quality = _classify_data_quality(
        catalog_source=catalog_source,
        warnings=warnings,
        field_sources=field_sources,
    )

    return {
        "status": canonical_status,
        "distribution_type": distribution_type,
        "data_quality": data_quality,
        "field_sources": field_sources,
        "last_verified_at": _last_verified_at(movie, analytics),
        "warnings": warnings,
        **forecast,
    }


def derive_canonical_status(movie: Movie, today: date | None = None) -> str:
    active_today = today or date.today()
    if movie.release_date <= active_today:
        return "released"
    if movie.status == "announced":
        return "announced"
    return "upcoming"


def _infer_catalog_source(movie: Movie) -> FieldSource:
    if movie.poster_url and "image.tmdb.org" in movie.poster_url:
        return "sourced"
    if movie.backdrop_url and "image.tmdb.org" in movie.backdrop_url:
        return "sourced"
    if movie.slug in SEEDED_MOVIE_SLUGS:
        return "generated"
    return "sourced"


def _enrichment_source(movie: Movie, enrichment: dict, field_name: str) -> FieldSource:
    value = enrichment.get(field_name)
    if value in (None, "", []):
        return "missing"
    return "generated" if movie.slug in SEEDED_MOVIE_SLUGS else "sourced"


def _build_warnings(
    movie: Movie,
    *,
    canonical_status: str,
    catalog_source: FieldSource,
    distribution_type: str,
    forecast: dict,
    analytics: MovieAnalytics | None,
    omdb_metadata: dict,
) -> list[str]:
    warnings: list[str] = []

    if movie.status != canonical_status:
        warnings.append(
            f"Stored movie status '{movie.status}' did not match the canonical release-date classification '{canonical_status}'."
        )
    if movie.release_date < date.today() and movie.status in {"upcoming", "announced"}:
        warnings.append("Release date is in the past, but the stored status was not marked as released.")
    if movie.release_date >= date.today() and movie.status == "released":
        warnings.append("Release date is in the future, but the stored status was marked as released.")
    if catalog_source == "generated":
        warnings.append("Core metadata is currently coming from local demo fallback data, not a live provider feed.")
    if distribution_type == "streaming-first" and (
        (analytics and analytics.predicted_opening_weekend_usd > 0)
        or (analytics and analytics.predicted_domestic_total_usd > 0)
    ):
        warnings.append("The title appears to be streaming-first, so theatrical box office forecasts were suppressed.")
    if not forecast["forecast_is_public"] and omdb_metadata.get("box_office") is None:
        warnings.append("No sourced theatrical revenue evidence is available for this title.")
    if analytics and any(
        value > 0
        for value in (
            analytics.youtube_views,
            analytics.youtube_likes,
            analytics.youtube_comments,
            analytics.x_mentions,
            analytics.reddit_mentions,
            analytics.google_trends_score,
        )
    ):
        warnings.append("Audience attention metrics are modeled estimates unless a provider feed explicitly verifies them.")

    # Deduplicate while preserving order.
    return list(dict.fromkeys(warnings))


def _classify_data_quality(
    *,
    catalog_source: FieldSource,
    warnings: list[str],
    field_sources: dict[str, FieldSource],
) -> str:
    critical_warning = any(
        "did not match" in warning or "past" in warning or "future" in warning
        for warning in warnings
    )
    sourced_fields = sum(1 for source in field_sources.values() if source == "sourced")

    if critical_warning:
        return "low"
    if catalog_source == "generated":
        return "low" if sourced_fields < 5 else "medium"
    if len(warnings) >= 3:
        return "medium"
    if sourced_fields >= 6:
        return "high"
    return "medium"


def _last_verified_at(movie: Movie, analytics: MovieAnalytics | None) -> datetime | None:
    candidates = [movie.updated_at, movie.created_at]
    if analytics is not None:
        candidates.extend([analytics.last_updated])
    return max((candidate.replace(tzinfo=timezone.utc) if candidate.tzinfo is None else candidate for candidate in candidates if candidate is not None), default=None)
