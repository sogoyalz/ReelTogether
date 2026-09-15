"""Account-owned movie taste feedback."""
from alembic import op
import sqlalchemy as sa

revision = "20260913_0005"
down_revision = "20260913_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("movie_feedback",
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("preference", sa.String(12), nullable=False))


def downgrade():
    op.drop_table("movie_feedback")
