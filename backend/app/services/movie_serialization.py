"""Public movie DTOs shared by APIs without coupling route modules."""
from app.models.movie import Movie
from app.schemas.movie import MovieSummary
from app.repositories import movies as movie_repository
from app.services.catalog_enrichment import get_enrichment
from app.services.movie_data import build_movie_data_contract
from app.services.provider_metadata import normalize_metadata


def latest_analytics(movie: Movie):
    return movie_repository.latest_analytics(movie)


def analytics_payload(movie: Movie) -> dict:
    analytics = latest_analytics(movie)
    if analytics is None:
        return {
            "trailer_url": None,
            "youtube_views": 0,
            "youtube_likes": 0,
            "youtube_comments": 0,
            "google_trends_score": 0.0,
            "x_mentions": 0,
            "reddit_mentions": 0,
            "sentiment_score": 0.0,
            "buzz_score": 0.0,
            "hype_score": 0.0,
            "predicted_opening_weekend_usd": 0.0,
            "predicted_domestic_total_usd": 0.0,
        }

    return {
        "trailer_url": analytics.trailer_url,
        "youtube_views": analytics.youtube_views,
        "youtube_likes": analytics.youtube_likes,
        "youtube_comments": analytics.youtube_comments,
        "google_trends_score": analytics.google_trends_score,
        "x_mentions": analytics.x_mentions,
        "reddit_mentions": analytics.reddit_mentions,
        "sentiment_score": analytics.sentiment_score,
        "buzz_score": analytics.buzz_score,
        "hype_score": analytics.hype_score,
        "predicted_opening_weekend_usd": analytics.predicted_opening_weekend_usd,
        "predicted_domestic_total_usd": analytics.predicted_domestic_total_usd,
    }


def serialize_summary(movie: Movie) -> MovieSummary:
    """Serialize public summaries using only persisted catalog facts."""
    analytics = analytics_payload(movie)
    enrichment = get_enrichment(movie)
    metadata = normalize_metadata(movie.provider_metadata)

    return MovieSummary(
        id=movie.id,
        tmdb_id=movie.tmdb_id,
        slug=movie.slug,
        title=movie.title,
        release_date=movie.release_date,
        **{key: value for key, value in build_movie_data_contract(movie, analytics=latest_analytics(movie), enrichment=enrichment, omdb_metadata=metadata).items() if key in MovieSummary.model_fields},
        poster_url=movie.poster_url,
        backdrop_url=movie.backdrop_url,
        overview=movie.overview,
        genres=movie.genres,
        tmdb_popularity=movie.tmdb_popularity,
        buzz_score=analytics["buzz_score"],
        hype_score=analytics["hype_score"],
        franchise=enrichment["franchise"],
        studios=enrichment["studios"],
        streaming_on=enrichment["streaming_on"],
        directors=enrichment["directors"],
        cast=enrichment["cast"],
        imdb_rating=metadata.get("imdb_rating"),
        rated=metadata.get("rated"),
        runtime=metadata.get("runtime"),
        rotten_tomatoes=metadata.get("rotten_tomatoes"),
        logo_url=enrichment.get("logo_url"),
    )
