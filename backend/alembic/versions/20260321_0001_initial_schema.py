"""Initial schema

Revision ID: 20260321_0001
Revises:
Create Date: 2026-03-21 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260321_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "movies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("release_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("poster_url", sa.String(length=500), nullable=True),
        sa.Column("backdrop_url", sa.String(length=500), nullable=True),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("genres", sa.JSON(), nullable=False),
        sa.Column("tmdb_popularity", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_movies_id", "movies", ["id"])
    op.create_index("ix_movies_tmdb_id", "movies", ["tmdb_id"], unique=True)
    op.create_index("ix_movies_slug", "movies", ["slug"], unique=True)
    op.create_index("ix_movies_title", "movies", ["title"])
    op.create_index("ix_movies_release_date", "movies", ["release_date"])

    op.create_table(
        "movie_analytics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id"), nullable=False),
        sa.Column("snapshot_label", sa.String(length=64), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("youtube_views", sa.Integer(), nullable=False),
        sa.Column("youtube_likes", sa.Integer(), nullable=False),
        sa.Column("youtube_comments", sa.Integer(), nullable=False),
        sa.Column("google_trends_score", sa.Float(), nullable=False),
        sa.Column("x_mentions", sa.Integer(), nullable=False),
        sa.Column("reddit_mentions", sa.Integer(), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=False),
        sa.Column("sentiment_positive", sa.Integer(), nullable=False),
        sa.Column("sentiment_neutral", sa.Integer(), nullable=False),
        sa.Column("sentiment_negative", sa.Integer(), nullable=False),
        sa.Column("momentum_score", sa.Float(), nullable=False),
        sa.Column("buzz_score", sa.Float(), nullable=False),
        sa.Column("hype_score", sa.Float(), nullable=False),
        sa.Column("predicted_opening_weekend_usd", sa.Float(), nullable=False),
        sa.Column("predicted_domestic_total_usd", sa.Float(), nullable=False),
        sa.Column("trailer_url", sa.String(length=500), nullable=True),
        sa.Column("last_updated", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_movie_analytics_id", "movie_analytics", ["id"])
    op.create_index("ix_movie_analytics_movie_id", "movie_analytics", ["movie_id"])
    op.create_index("ix_movie_analytics_snapshot_date", "movie_analytics", ["snapshot_date"])

    op.create_table(
        "movie_discussions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id"), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author", sa.String(length=128), nullable=True),
        sa.Column("engagement_score", sa.Float(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("raw_payload", sa.Text(), nullable=True),
    )
    op.create_index("ix_movie_discussions_id", "movie_discussions", ["id"])
    op.create_index("ix_movie_discussions_movie_id", "movie_discussions", ["movie_id"])
    op.create_index("ix_movie_discussions_source", "movie_discussions", ["source"])
    op.create_index("ix_movie_discussions_external_id", "movie_discussions", ["external_id"], unique=True)
    op.create_index("ix_movie_discussions_created_at", "movie_discussions", ["created_at"])

    op.create_table(
        "movie_sentiment_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id"), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("positive_count", sa.Integer(), nullable=False),
        sa.Column("neutral_count", sa.Integer(), nullable=False),
        sa.Column("negative_count", sa.Integer(), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_movie_sentiment_snapshots_id", "movie_sentiment_snapshots", ["id"])
    op.create_index("ix_movie_sentiment_snapshots_movie_id", "movie_sentiment_snapshots", ["movie_id"])
    op.create_index("ix_movie_sentiment_snapshots_snapshot_at", "movie_sentiment_snapshots", ["snapshot_at"])

    op.create_table(
        "movie_prediction_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id"), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("predicted_opening_weekend_usd", sa.Float(), nullable=False),
        sa.Column("predicted_domestic_total_usd", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("feature_version", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_movie_prediction_snapshots_id", "movie_prediction_snapshots", ["id"])
    op.create_index("ix_movie_prediction_snapshots_movie_id", "movie_prediction_snapshots", ["movie_id"])
    op.create_index("ix_movie_prediction_snapshots_snapshot_at", "movie_prediction_snapshots", ["snapshot_at"])

    op.create_table(
        "movie_feature_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id"), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("release_days_until", sa.Integer(), nullable=False),
        sa.Column("trailer_views", sa.Integer(), nullable=False),
        sa.Column("likes_to_views_ratio", sa.Float(), nullable=False),
        sa.Column("comments_to_views_ratio", sa.Float(), nullable=False),
        sa.Column("reddit_mentions", sa.Integer(), nullable=False),
        sa.Column("social_mentions", sa.Integer(), nullable=False),
        sa.Column("tmdb_popularity", sa.Float(), nullable=False),
        sa.Column("imdb_rating", sa.Float(), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=False),
        sa.Column("feature_version", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_movie_feature_snapshots_id", "movie_feature_snapshots", ["id"])
    op.create_index("ix_movie_feature_snapshots_movie_id", "movie_feature_snapshots", ["movie_id"])
    op.create_index("ix_movie_feature_snapshots_snapshot_at", "movie_feature_snapshots", ["snapshot_at"])

    op.create_table(
        "movie_summary_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id"), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("audience_summary", sa.Text(), nullable=False),
        sa.Column("critic_summary", sa.Text(), nullable=False),
        sa.Column("key_themes", sa.Text(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_movie_summary_snapshots_id", "movie_summary_snapshots", ["id"])
    op.create_index("ix_movie_summary_snapshots_movie_id", "movie_summary_snapshots", ["movie_id"])
    op.create_index("ix_movie_summary_snapshots_snapshot_at", "movie_summary_snapshots", ["snapshot_at"])


def downgrade() -> None:
    op.drop_index("ix_movie_summary_snapshots_snapshot_at", table_name="movie_summary_snapshots")
    op.drop_index("ix_movie_summary_snapshots_movie_id", table_name="movie_summary_snapshots")
    op.drop_index("ix_movie_summary_snapshots_id", table_name="movie_summary_snapshots")
    op.drop_table("movie_summary_snapshots")

    op.drop_index("ix_movie_feature_snapshots_snapshot_at", table_name="movie_feature_snapshots")
    op.drop_index("ix_movie_feature_snapshots_movie_id", table_name="movie_feature_snapshots")
    op.drop_index("ix_movie_feature_snapshots_id", table_name="movie_feature_snapshots")
    op.drop_table("movie_feature_snapshots")

    op.drop_index("ix_movie_prediction_snapshots_snapshot_at", table_name="movie_prediction_snapshots")
    op.drop_index("ix_movie_prediction_snapshots_movie_id", table_name="movie_prediction_snapshots")
    op.drop_index("ix_movie_prediction_snapshots_id", table_name="movie_prediction_snapshots")
    op.drop_table("movie_prediction_snapshots")

    op.drop_index("ix_movie_sentiment_snapshots_snapshot_at", table_name="movie_sentiment_snapshots")
    op.drop_index("ix_movie_sentiment_snapshots_movie_id", table_name="movie_sentiment_snapshots")
    op.drop_index("ix_movie_sentiment_snapshots_id", table_name="movie_sentiment_snapshots")
    op.drop_table("movie_sentiment_snapshots")

    op.drop_index("ix_movie_discussions_created_at", table_name="movie_discussions")
    op.drop_index("ix_movie_discussions_external_id", table_name="movie_discussions")
    op.drop_index("ix_movie_discussions_source", table_name="movie_discussions")
    op.drop_index("ix_movie_discussions_movie_id", table_name="movie_discussions")
    op.drop_index("ix_movie_discussions_id", table_name="movie_discussions")
    op.drop_table("movie_discussions")

    op.drop_index("ix_movie_analytics_snapshot_date", table_name="movie_analytics")
    op.drop_index("ix_movie_analytics_movie_id", table_name="movie_analytics")
    op.drop_index("ix_movie_analytics_id", table_name="movie_analytics")
    op.drop_table("movie_analytics")

    op.drop_index("ix_movies_release_date", table_name="movies")
    op.drop_index("ix_movies_title", table_name="movies")
    op.drop_index("ix_movies_slug", table_name="movies")
    op.drop_index("ix_movies_tmdb_id", table_name="movies")
    op.drop_index("ix_movies_id", table_name="movies")
    op.drop_table("movies")
