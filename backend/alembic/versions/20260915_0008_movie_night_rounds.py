"""Version movie-night ballots across restarted rounds."""
from alembic import op
import sqlalchemy as sa
revision = "20260915_0008"
down_revision = "20260914_0007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("movie_nights", sa.Column("round_id", sa.Integer(), nullable=False, server_default="0"))
    op.execute("UPDATE movie_nights SET round_id = 1 WHERE state <> 'lobby'")


def downgrade():
    with op.batch_alter_table("movie_nights") as batch:
        batch.drop_column("round_id")
