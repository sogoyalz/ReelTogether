from __future__ import annotations

import math

from app.models.ai import MovieFeatureSnapshot, MoviePredictionSnapshot, MovieSentimentSnapshot
from app.models.movie import Movie, MovieAnalytics
from app.services.model_training import FEATURE_COLUMNS, load_box_office_artifact, predict_from_artifact
from app.services.review_analysis import analyze_review_landscape
from app.services.omdb import fetch_movie_metadata


def build_prediction_payload(
    movie: Movie,
    analytics: MovieAnalytics | None,
    feature_snapshot: MovieFeatureSnapshot,
    sentiment_snapshot: MovieSentimentSnapshot | None,
    enrichment: dict,
) -> dict:
    trained_prediction = _predict_with_trained_artifact(movie, analytics, feature_snapshot, sentiment_snapshot, enrichment)
    feature_values = {
        "Trailer reach": _bounded(_log_scale(feature_snapshot.trailer_views, 50_000_000)),
        "Engagement quality": _bounded(
            feature_snapshot.likes_to_views_ratio * 7 + feature_snapshot.comments_to_views_ratio * 40
        ),
        "Conversation volume": _bounded(_log_scale(feature_snapshot.social_mentions, 400_000)),
        "Search demand": _bounded((analytics.google_trends_score if analytics else 0.0) / 100),
        "TMDB popularity": _bounded(feature_snapshot.tmdb_popularity / 100),
        "Critic strength": _bounded(feature_snapshot.imdb_rating / 10),
        "Audience sentiment": _bounded((feature_snapshot.sentiment_score + 1) / 2),
        "Franchise lift": 0.82 if enrichment.get("franchise") else 0.36,
        "Release timing": _release_timing_score(feature_snapshot.release_days_until, movie.status),
    }

    weights = {
        "Trailer reach": 0.2,
        "Engagement quality": 0.12,
        "Conversation volume": 0.14,
        "Search demand": 0.12,
        "TMDB popularity": 0.12,
        "Critic strength": 0.08,
        "Audience sentiment": 0.1,
        "Franchise lift": 0.07,
        "Release timing": 0.05,
    }

    weighted_score = sum(feature_values[label] * weight for label, weight in weights.items())
    opening_base = 12_000_000 + weighted_score * 185_000_000
    status_multiplier = {
        "announced": 0.92,
        "upcoming": 1.0,
        "released": 1.05,
    }.get(movie.status, 1.0)
    opening = round(opening_base * status_multiplier, 2)

    domestic_multiple = 2.25 + feature_values["Audience sentiment"] * 0.65 + feature_values["Critic strength"] * 0.3
    if enrichment.get("franchise"):
        domestic_multiple += 0.2
    domestic = round(opening * domestic_multiple, 2)

    if trained_prediction is not None:
        blend_weight = _trained_model_weight(trained_prediction["artifact"])
        opening = round((opening * (1 - blend_weight)) + (trained_prediction["opening"] * blend_weight), 2)
        domestic = round((domestic * (1 - blend_weight)) + (trained_prediction["domestic"] * blend_weight), 2)

    signal_consistency = 1 - abs(feature_values["Search demand"] - feature_values["Trailer reach"])
    sample_richness = min(1.0, (feature_snapshot.social_mentions + feature_snapshot.trailer_views / 2000) / 75_000)
    sentiment_support = _bounded((sentiment_snapshot.sentiment_score + 1) / 2 if sentiment_snapshot else feature_values["Audience sentiment"])
    confidence = round(_bounded(0.35 + signal_consistency * 0.25 + sample_richness * 0.2 + sentiment_support * 0.2), 2)

    range_spread = max(0.12, 0.34 - confidence * 0.18)
    opening_low = round(opening * (1 - range_spread), 2)
    opening_high = round(opening * (1 + range_spread), 2)
    domestic_low = round(domestic * (1 - range_spread * 0.85), 2)
    domestic_high = round(domestic * (1 + range_spread * 0.85), 2)

    contribution_total = sum(abs(feature_values[label] * weights[label]) for label in weights) or 1.0
    feature_importance = [
        {
            "label": label,
            "value": round(feature_values[label], 2),
            "impact_score": round(abs(feature_values[label] * weights[label]) / contribution_total, 2),
            "direction": "positive" if feature_values[label] >= 0.5 else "watch",
            "explanation": _explain_feature(label, feature_values[label]),
        }
        for label in sorted(weights, key=lambda item: abs(feature_values[item] * weights[item]), reverse=True)
    ]

    methodology = (
        "The forecast blends trailer reach, engagement quality, conversation volume, search demand, "
        "critic strength, audience sentiment, franchise lift, and release timing into a weighted revenue model."
    )

    return {
        "predicted_opening_weekend_usd": opening,
        "predicted_domestic_total_usd": domestic,
        "confidence_score": confidence,
        "opening_weekend_low_usd": opening_low,
        "opening_weekend_high_usd": opening_high,
        "domestic_total_low_usd": domestic_low,
        "domestic_total_high_usd": domestic_high,
        "feature_importance": feature_importance,
        "methodology": methodology,
    }


def apply_prediction_snapshot(
    snapshot: MoviePredictionSnapshot,
    payload: dict,
    *,
    feature_version: str,
    model_version: str,
) -> None:
    snapshot.predicted_opening_weekend_usd = payload["predicted_opening_weekend_usd"]
    snapshot.predicted_domestic_total_usd = payload["predicted_domestic_total_usd"]
    snapshot.confidence_score = payload["confidence_score"]
    snapshot.feature_version = feature_version
    snapshot.model_version = model_version


def _bounded(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def _log_scale(value: float, ceiling: float) -> float:
    if value <= 0:
        return 0.0
    return math.log1p(value) / math.log1p(ceiling)


def _release_timing_score(days_until_release: int, status: str) -> float:
    if status == "released":
        return 0.72
    distance = abs(days_until_release)
    if distance <= 30:
        return 0.95
    if distance <= 90:
        return 0.82
    if distance <= 180:
        return 0.67
    return 0.48


def _explain_feature(label: str, value: float) -> str:
    strength = "strong" if value >= 0.7 else "moderate" if value >= 0.45 else "limited"
    return f"{label} is currently a {strength} driver in the forecast."


def _predict_with_trained_artifact(
    movie: Movie,
    analytics: MovieAnalytics | None,
    feature_snapshot: MovieFeatureSnapshot,
    sentiment_snapshot: MovieSentimentSnapshot | None,
    enrichment: dict,
) -> dict[str, float] | None:
    artifact = load_box_office_artifact()
    if artifact is None:
        return None

    review_landscape = analyze_review_landscape(movie, movie.discussions, enrichment, fetch_movie_metadata(movie) or {})
    feature_map = {
        "trailer_views_log": round(math.log1p(feature_snapshot.trailer_views), 6),
        "likes_to_views_ratio": feature_snapshot.likes_to_views_ratio,
        "comments_to_views_ratio": feature_snapshot.comments_to_views_ratio,
        "social_mentions_log": round(math.log1p(feature_snapshot.social_mentions), 6),
        "tmdb_popularity": feature_snapshot.tmdb_popularity,
        "imdb_rating": feature_snapshot.imdb_rating,
        "sentiment_score": sentiment_snapshot.sentiment_score if sentiment_snapshot else feature_snapshot.sentiment_score,
        "critic_sentiment": review_landscape["critics"].sentiment_score,
        "audience_sentiment": review_landscape["audience"].sentiment_score,
        "critic_alignment": review_landscape["alignment_score"],
        "franchise_flag": 1.0 if enrichment.get("franchise") else 0.0,
        "genre_family": 1.0 if "Family" in movie.genres or "Animation" in movie.genres else 0.0,
        "genre_action": 1.0 if "Action" in movie.genres else 0.0,
        "genre_drama": 1.0 if "Drama" in movie.genres else 0.0,
        "genre_comedy": 1.0 if "Comedy" in movie.genres else 0.0,
        "release_month": movie.release_date.month / 12,
    }
    for column in FEATURE_COLUMNS:
        feature_map.setdefault(column, 0.0)
    predictions = predict_from_artifact(artifact, feature_map)
    predictions["artifact"] = artifact
    return predictions


def is_non_theatrical_release(
    movie: Movie,
    *,
    enrichment: dict | None = None,
    box_office: str | None = None,
) -> bool:
    """Return True if a title is very likely streaming-first / non-theatrical."""
    enrichment = enrichment or {}
    streaming_providers = enrichment.get("streaming_on", [])
    studios = [s.lower() for s in enrichment.get("studios", [])]

    # Already has real box-office revenue → definitely theatrical
    if box_office and box_office not in ("N/A", "", None):
        return False

    # Released but zero theatrical revenue and distributed on a streaming platform
    if movie.status == "released" and streaming_providers and not any(
        word in " ".join(studios) for word in ("disney", "universal", "warner", "paramount", "sony", "lionsgate")
    ):
        return True

    # Streaming platforms as the only known distributor for upcoming titles
    streaming_only_platforms = {"netflix", "amazon prime", "apple tv+", "disney+", "hulu", "max", "hbo max", "peacock"}
    providers_lower = {p.lower() for p in streaming_providers}
    if providers_lower and providers_lower.issubset(streaming_only_platforms) and not studios:
        return True

    return False


def normalize_public_forecast(
    movie: Movie,
    *,
    enrichment: dict | None = None,
    box_office: str | None = None,
    opening: float = 0.0,
    domestic: float = 0.0,
    confidence: float = 0.0,
    opening_low: float = 0.0,
    opening_high: float = 0.0,
    domestic_low: float = 0.0,
    domestic_high: float = 0.0,
) -> dict:
    """Build a sanitised forecast payload for public consumption."""
    enrichment = enrichment or {}
    non_theatrical = is_non_theatrical_release(movie, enrichment=enrichment, box_office=box_office)

    # Suppress theatrical forecasts for streaming-first titles
    if non_theatrical:
        return {
            "predicted_opening_weekend_usd": 0.0,
            "predicted_domestic_total_usd": 0.0,
            "confidence_score": 0.0,
            "opening_weekend_low_usd": 0.0,
            "opening_weekend_high_usd": 0.0,
            "domestic_total_low_usd": 0.0,
            "domestic_total_high_usd": 0.0,
            "forecast_is_public": False,
            "forecast_status": "suppressed",
            "forecast_note": "Theatrical forecast suppressed — title appears to be streaming-first.",
            "engagement_metrics_are_estimated": True,
            "engagement_metrics_note": "Audience attention metrics are modeled estimates.",
            "methodology": None,
            "feature_importance": [],
        }

    # Use real box-office data if available (released films)
    if box_office and box_office not in ("N/A", "", None):
        return {
            "predicted_opening_weekend_usd": 0.0,
            "predicted_domestic_total_usd": 0.0,
            "confidence_score": 1.0,
            "opening_weekend_low_usd": 0.0,
            "opening_weekend_high_usd": 0.0,
            "domestic_total_low_usd": 0.0,
            "domestic_total_high_usd": 0.0,
            "forecast_is_public": True,
            "forecast_status": "actuals_available",
            "forecast_note": "Sourced box-office actuals are available via OMDB.",
            "engagement_metrics_are_estimated": True,
            "engagement_metrics_note": "Box-office actuals do not verify audience attention estimates.",
            "methodology": None,
            "feature_importance": [],
        }

    forecast_is_public = opening > 0 or domestic > 0
    return {
        "predicted_opening_weekend_usd": round(opening, 2) if opening else 0.0,
        "predicted_domestic_total_usd": round(domestic, 2) if domestic else 0.0,
        "confidence_score": round(confidence, 2),
        "opening_weekend_low_usd": round(opening_low, 2) if opening_low else 0.0,
        "opening_weekend_high_usd": round(opening_high, 2) if opening_high else 0.0,
        "domestic_total_low_usd": round(domestic_low, 2) if domestic_low else 0.0,
        "domestic_total_high_usd": round(domestic_high, 2) if domestic_high else 0.0,
        "forecast_is_public": forecast_is_public,
        "forecast_status": "modeled" if forecast_is_public else "unavailable",
        "forecast_note": "Forecast is a model estimate based on social signals, trailer reach, and engagement data."
        if forecast_is_public
        else "Insufficient data to generate a public forecast for this title.",
        "engagement_metrics_are_estimated": True,
        "engagement_metrics_note": "Audience attention metrics are modeled estimates unless a provider feed explicitly verifies them.",
        "methodology": "Weighted feature model combining trailer reach, social buzz, search demand, sentiment, and franchise signals.",
        "feature_importance": [],
    }


def _trained_model_weight(artifact: dict) -> float:
    training_count = artifact.get("training_count", 0)
    opening_mape = artifact.get("targets", {}).get("opening", {}).get("test_metrics", {}).get("mape", 100.0)
    domestic_mape = artifact.get("targets", {}).get("domestic", {}).get("test_metrics", {}).get("mape", 100.0)
    average_mape = (opening_mape + domestic_mape) / 2
    count_weight = min(0.55, training_count / 30)
    quality_weight = max(0.12, min(0.6, 1 - (average_mape / 100)))
    return round(max(0.18, min(0.45, count_weight * quality_weight)), 2)
