"""Persist browse enrichment and align cascade constraints."""
from alembic import op
import sqlalchemy as sa

revision = "20260913_0003"
down_revision = "20260324_0002"
branch_labels = None
depends_on = None

AI_TABLES = ("movie_discussions", "movie_sentiment_snapshots", "movie_feature_snapshots", "movie_prediction_snapshots", "movie_summary_snapshots", "review_sentiments")
CONVENTION = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}


def upgrade():
    op.add_column("movies", sa.Column("enrichment_data", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("movies", sa.Column("provider_metadata", sa.JSON(), nullable=False, server_default="{}"))
    for table in AI_TABLES:
        with op.batch_alter_table(table, naming_convention=CONVENTION) as batch:
            batch.drop_constraint(f"fk_{table}_movie_id_movies", type_="foreignkey")
            batch.create_foreign_key(f"fk_{table}_movie_id_movies", "movies", ["movie_id"], ["id"], ondelete="CASCADE")


def downgrade():
    for table in AI_TABLES:
        with op.batch_alter_table(table, naming_convention=CONVENTION) as batch:
            batch.drop_constraint(f"fk_{table}_movie_id_movies", type_="foreignkey")
            batch.create_foreign_key(f"fk_{table}_movie_id_movies", "movies", ["movie_id"], ["id"], ondelete="CASCADE" if table == "review_sentiments" else None)
    op.drop_column("movies", "provider_metadata")
    op.drop_column("movies", "enrichment_data")
