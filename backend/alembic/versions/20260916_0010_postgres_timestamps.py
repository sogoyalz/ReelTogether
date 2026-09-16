"""Align PostgreSQL snapshot timestamps with timezone-aware models."""
from alembic import op
import sqlalchemy as sa
revision = '20260916_0010'
down_revision = '20260915_0009'
branch_labels = None
depends_on = None
COLUMNS = [('movie_discussions','created_at'), ('movie_feature_snapshots','snapshot_at'),
           ('movie_prediction_snapshots','snapshot_at'), ('movie_sentiment_snapshots','snapshot_at'),
           ('movie_summary_snapshots','snapshot_at')]


def upgrade():
    if op.get_bind().dialect.name == 'postgresql':
        for table, column in COLUMNS:
            op.alter_column(table, column, type_=sa.DateTime(timezone=True),
                            postgresql_using=f"{column} AT TIME ZONE 'UTC'")


def downgrade():
    if op.get_bind().dialect.name == 'postgresql':
        for table, column in COLUMNS:
            op.alter_column(table, column, type_=sa.DateTime(),
                            postgresql_using=f"{column} AT TIME ZONE 'UTC'")
