"""add ratings and review sentiments

Revision ID: 20260324_0002
Revises: 20260321_0001
Create Date: 2026-03-24 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260324_0002"
down_revision = "20260321_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_sentiments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("content_snippet", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("sentiment_label", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_review_sentiments_id"), "review_sentiments", ["id"], unique=False)
    op.create_index(op.f("ix_review_sentiments_movie_id"), "review_sentiments", ["movie_id"], unique=False)
    op.create_index(op.f("ix_review_sentiments_author"), "review_sentiments", ["author"], unique=False)
    op.create_index(op.f("ix_review_sentiments_created_at"), "review_sentiments", ["created_at"], unique=False)
    op.create_index(op.f("ix_review_sentiments_sentiment_label"), "review_sentiments", ["sentiment_label"], unique=False)
    op.create_index(op.f("ix_review_sentiments_source"), "review_sentiments", ["source"], unique=False)
    op.create_index(op.f("ix_review_sentiments_analyzed_at"), "review_sentiments", ["analyzed_at"], unique=False)

    op.create_table(
        "user_ratings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "movie_id", name="uq_user_ratings_session_movie"),
    )
    op.create_index(op.f("ix_user_ratings_id"), "user_ratings", ["id"], unique=False)
    op.create_index(op.f("ix_user_ratings_movie_id"), "user_ratings", ["movie_id"], unique=False)
    op.create_index(op.f("ix_user_ratings_session_id"), "user_ratings", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_ratings_session_id"), table_name="user_ratings")
    op.drop_index(op.f("ix_user_ratings_movie_id"), table_name="user_ratings")
    op.drop_index(op.f("ix_user_ratings_id"), table_name="user_ratings")
    op.drop_table("user_ratings")

    op.drop_index(op.f("ix_review_sentiments_analyzed_at"), table_name="review_sentiments")
    op.drop_index(op.f("ix_review_sentiments_source"), table_name="review_sentiments")
    op.drop_index(op.f("ix_review_sentiments_sentiment_label"), table_name="review_sentiments")
    op.drop_index(op.f("ix_review_sentiments_created_at"), table_name="review_sentiments")
    op.drop_index(op.f("ix_review_sentiments_author"), table_name="review_sentiments")
    op.drop_index(op.f("ix_review_sentiments_movie_id"), table_name="review_sentiments")
    op.drop_index(op.f("ix_review_sentiments_id"), table_name="review_sentiments")
    op.drop_table("review_sentiments")
