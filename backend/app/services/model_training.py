from __future__ import annotations

from app.services.provider_metadata import normalize_metadata

import json
import math
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai import MovieFeatureSnapshot, MovieSentimentSnapshot
from app.models.movie import Movie
from app.services.catalog_enrichment import get_enrichment
from app.services.omdb import fetch_movie_metadata
from app.services.review_analysis import analyze_review_landscape

ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "model_artifacts"
BOX_OFFICE_ARTIFACT = ARTIFACT_DIR / "box_office_forecaster.json"

FEATURE_COLUMNS = [
    "trailer_views_log",
    "likes_to_views_ratio",
    "comments_to_views_ratio",
    "social_mentions_log",
    "tmdb_popularity",
    "imdb_rating",
    "sentiment_score",
    "critic_sentiment",
    "audience_sentiment",
    "critic_alignment",
    "franchise_flag",
    "genre_family",
    "genre_action",
    "genre_drama",
    "genre_comedy",
    "release_month",
]


@dataclass
class DataRow:
    movie_id: int
    slug: str
    release_date: date
    features: dict[str, float]
    opening_target: float
    domestic_target: float


def train_and_save_box_office_model(db: Session) -> dict:
    rows = build_training_rows(db)
    split = split_rows(rows)
    artifact = {
        "model_version": "box-office-linear-v1",
        "trained_on": date.today().isoformat(),
        "feature_columns": FEATURE_COLUMNS,
        "training_count": len(split["train"]),
        "validation_count": len(split["validation"]),
        "test_count": len(split["test"]),
        "targets": {},
    }

    train_X = _matrix(split["train"])
    val_X = _matrix(split["validation"])
    test_X = _matrix(split["test"])

    for target_name, attr in [("opening", "opening_target"), ("domestic", "domestic_target")]:
        train_y = [getattr(row, attr) for row in split["train"]]
        val_y = [getattr(row, attr) for row in split["validation"]]
        test_y = [getattr(row, attr) for row in split["test"]]

        model = fit_linear_regression(train_X, train_y)
        validation_metrics = evaluate_model(model, val_X, val_y)
        test_metrics = evaluate_model(model, test_X, test_y)

        artifact["targets"][target_name] = {
            "intercept": model["intercept"],
            "coefficients": model["coefficients"],
            "feature_means": model["feature_means"],
            "feature_stds": model["feature_stds"],
            "residual_std": model["residual_std"],
            "validation_metrics": validation_metrics,
            "test_metrics": test_metrics,
        }

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    BOX_OFFICE_ARTIFACT.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    return artifact


def load_box_office_artifact() -> dict | None:
    if not BOX_OFFICE_ARTIFACT.exists():
        return None
    try:
        return json.loads(BOX_OFFICE_ARTIFACT.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def build_training_rows(db: Session) -> list[DataRow]:
    movies = db.scalars(select(Movie).order_by(Movie.release_date.asc())).all()
    rows: list[DataRow] = []
    for movie in movies:
        feature_snapshot = db.scalar(
            select(MovieFeatureSnapshot)
            .where(MovieFeatureSnapshot.movie_id == movie.id, MovieFeatureSnapshot.snapshot_at < datetime.combine(movie.release_date, datetime.min.time()), MovieFeatureSnapshot.feature_version == "observed-v1")
            .order_by(MovieFeatureSnapshot.snapshot_at.desc())
        )
        sentiment_snapshot = db.scalar(
            select(MovieSentimentSnapshot)
            .where(MovieSentimentSnapshot.movie_id == movie.id, MovieSentimentSnapshot.snapshot_at < datetime.combine(movie.release_date, datetime.min.time()))
            .order_by(MovieSentimentSnapshot.snapshot_at.desc())
        )
        if feature_snapshot is None:
            continue

        opening_target, domestic_target = _targets_for_movie(movie)
        if opening_target <= 0 or domestic_target <= 0:
            continue

        enrichment = get_enrichment(movie)
        omdb = {}
        discussions = [d for d in movie.discussions if d.created_at.replace(tzinfo=None) <= feature_snapshot.snapshot_at.replace(tzinfo=None)]
        review_landscape = analyze_review_landscape(movie, discussions, enrichment, omdb)
        features = _feature_map(movie, feature_snapshot, sentiment_snapshot, review_landscape, enrichment)
        rows.append(
            DataRow(
                movie_id=movie.id,
                slug=movie.slug,
                release_date=movie.release_date,
                features=features,
                opening_target=opening_target,
                domestic_target=domestic_target,
            )
        )
    return rows


def split_rows(rows: list[DataRow]) -> dict[str, list[DataRow]]:
    ordered = sorted(rows, key=lambda row: row.release_date)
    if len(ordered) < 30:
        raise ValueError("Need at least 30 released titles with sourced revenue and observed pre-release features; demo estimates are not training data.")

    train_end = max(1, int(len(ordered) * 0.6))
    validation_end = max(train_end + 1, int(len(ordered) * 0.8))
    return {
        "train": ordered[:train_end],
        "validation": ordered[train_end:validation_end],
        "test": ordered[validation_end:],
    }


def predict_from_artifact(artifact: dict, features: dict[str, float]) -> dict[str, float]:
    results: dict[str, float] = {}
    for target_name in ("opening", "domestic"):
        payload = artifact["targets"][target_name]
        scaled = []
        for index, column in enumerate(artifact["feature_columns"]):
            value = features.get(column, 0.0)
            mean = payload["feature_means"][index]
            std = payload["feature_stds"][index] or 1.0
            scaled.append((value - mean) / std)
        prediction = payload["intercept"] + sum(
            coefficient * value for coefficient, value in zip(payload["coefficients"], scaled, strict=False)
        )
        results[target_name] = round(max(1_000_000.0, prediction), 2)
    return results


def fit_linear_regression(X: list[list[float]], y: list[float]) -> dict:
    if not X:
        return {
            "intercept": 0.0,
            "coefficients": [0.0 for _ in FEATURE_COLUMNS],
            "feature_means": [0.0 for _ in FEATURE_COLUMNS],
            "feature_stds": [1.0 for _ in FEATURE_COLUMNS],
            "residual_std": 0.0,
        }

    means = [sum(column) / len(column) for column in zip(*X, strict=False)]
    stds = []
    for index, mean in enumerate(means):
        variance = sum((row[index] - mean) ** 2 for row in X) / len(X)
        stds.append(math.sqrt(variance) or 1.0)

    normalized = [[(row[index] - means[index]) / stds[index] for index in range(len(FEATURE_COLUMNS))] for row in X]

    intercept = sum(y) / len(y)
    coefficients = [0.0 for _ in FEATURE_COLUMNS]
    learning_rate = 0.03
    iterations = 2200

    for _ in range(iterations):
        intercept_gradient = 0.0
        coefficient_gradients = [0.0 for _ in FEATURE_COLUMNS]
        for row, target in zip(normalized, y, strict=False):
            prediction = intercept + sum(weight * value for weight, value in zip(coefficients, row, strict=False))
            error = prediction - target
            intercept_gradient += error
            for index, value in enumerate(row):
                coefficient_gradients[index] += error * value

        intercept -= learning_rate * (intercept_gradient / len(normalized))
        for index in range(len(coefficients)):
            coefficients[index] -= learning_rate * ((coefficient_gradients[index] / len(normalized)) + coefficients[index] * 0.001)

    residuals = []
    for row, target in zip(normalized, y, strict=False):
        prediction = intercept + sum(weight * value for weight, value in zip(coefficients, row, strict=False))
        residuals.append(target - prediction)
    residual_std = math.sqrt(sum(residual ** 2 for residual in residuals) / len(residuals)) if residuals else 0.0

    return {
        "intercept": round(intercept, 6),
        "coefficients": [round(value, 6) for value in coefficients],
        "feature_means": [round(value, 6) for value in means],
        "feature_stds": [round(value, 6) for value in stds],
        "residual_std": round(residual_std, 6),
    }


def evaluate_model(model: dict, X: list[list[float]], y: list[float]) -> dict:
    if not X or not y:
        raise ValueError("Cannot evaluate a model without held-out observations")

    predictions = []
    for row in X:
        scaled = [
            (row[index] - model["feature_means"][index]) / (model["feature_stds"][index] or 1.0)
            for index in range(len(FEATURE_COLUMNS))
        ]
        prediction = model["intercept"] + sum(
            coefficient * value for coefficient, value in zip(model["coefficients"], scaled, strict=False)
        )
        predictions.append(prediction)

    mae = sum(abs(actual - predicted) for actual, predicted in zip(y, predictions, strict=False)) / len(y)
    rmse = math.sqrt(sum((actual - predicted) ** 2 for actual, predicted in zip(y, predictions, strict=False)) / len(y))
    mape = (
        sum(abs((actual - predicted) / actual) for actual, predicted in zip(y, predictions, strict=False) if actual)
        / max(1, len([actual for actual in y if actual]))
    ) * 100
    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "mape": round(mape, 2),
    }


def _feature_map(
    movie: Movie,
    feature_snapshot: MovieFeatureSnapshot,
    sentiment_snapshot: MovieSentimentSnapshot | None,
    review_landscape: dict,
    enrichment: dict,
) -> dict[str, float]:
    genres = set(movie.genres)
    return {
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
        "genre_family": 1.0 if "Family" in genres or "Animation" in genres else 0.0,
        "genre_action": 1.0 if "Action" in genres else 0.0,
        "genre_drama": 1.0 if "Drama" in genres else 0.0,
        "genre_comedy": 1.0 if "Comedy" in genres else 0.0,
        "release_month": movie.release_date.month / 12,
    }


def _targets_for_movie(movie: Movie) -> tuple[float, float]:
    target = normalize_metadata(movie.provider_metadata).get("box_office_targets", {})
    if movie.release_date >= date.today() or not target.get("source_url") or not target.get("verified_at"):
        return 0.0, 0.0
    return float(target.get("opening_usd", 0)), float(target.get("domestic_usd", 0))


def _matrix(rows: list[DataRow]) -> list[list[float]]:
    return [[row.features[column] for column in FEATURE_COLUMNS] for row in rows]
